#!/usr/bin/env node

// src/index.ts
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema
} from "@modelcontextprotocol/sdk/types.js";
import express from "express";
import fs from "fs";
import path from "path";

// src/ws-bridge.ts
import { WebSocketServer, WebSocket } from "ws";
import http from "http";
var WS_OPEN = WebSocket.OPEN;
var ExtensionBridge = class {
  constructor(port = 9527, options) {
    this.port = port;
    this.silent = options?.silent ?? false;
    if (!this.silent) {
      if (this.token) {
        console.error("[Bridge] Token authentication enabled");
      } else {
        console.error("[Bridge] Warning: MCP_TOKEN not set, requests may be rejected by extension");
      }
    }
  }
  wss = null;
  httpServer = null;
  client = null;
  isServerMode = false;
  pendingRequests = /* @__PURE__ */ new Map();
  requestTimeout = 36e4;
  // 6 minutes (图片多时需要更长时间)
  connectionResolvers = [];
  // 安全验证 token（从环境变量读取，优先使用 WECHATSYNC_TOKEN）
  token = process.env.WECHATSYNC_TOKEN || process.env.MCP_TOKEN || "";
  // 是否静默模式（CLI 使用时不输出日志）
  silent = false;
  /**
   * 启动服务 - 自动选择服务器模式或客户端模式
   */
  async start() {
    try {
      await this.startServer();
      this.isServerMode = true;
      if (!this.silent) console.error(`[Bridge] Running as PRIMARY (WebSocket: ${this.port}, HTTP: ${this.port + 1})`);
    } catch (error) {
      if (error.code === "EADDRINUSE") {
        this.isServerMode = false;
        if (!this.silent) console.error(`[Bridge] Running as SECONDARY (forwarding to localhost:${this.port + 1})`);
      } else {
        throw error;
      }
    }
  }
  /**
   * 启动 WebSocket 服务器 + HTTP API
   */
  startServer() {
    return new Promise((resolve, reject) => {
      try {
        this.wss = new WebSocketServer({ port: this.port });
        this.wss.on("listening", () => {
          if (!this.silent) console.error(`[Bridge] WebSocket server listening on port ${this.port}`);
          this.startHttpApi().then(resolve).catch(reject);
        });
        this.wss.on("connection", (ws) => {
          if (!this.silent) console.error("[Bridge] Extension connected");
          this.client = ws;
          for (const resolver of this.connectionResolvers) {
            resolver();
          }
          this.connectionResolvers = [];
          ws.on("message", (data) => {
            this.handleMessage(data.toString());
          });
          ws.on("close", () => {
            if (!this.silent) console.error("[Bridge] Extension disconnected");
            this.client = null;
          });
          ws.on("error", (error) => {
            if (!this.silent) console.error("[Bridge] WebSocket error:", error);
          });
        });
        this.wss.on("error", (error) => {
          reject(error);
        });
      } catch (error) {
        reject(error);
      }
    });
  }
  /**
   * 启动 HTTP API 服务器（供其他 MCP 实例调用）
   */
  startHttpApi() {
    return new Promise((resolve, reject) => {
      this.httpServer = http.createServer(async (req, res) => {
        res.setHeader("Access-Control-Allow-Origin", "*");
        res.setHeader("Access-Control-Allow-Methods", "POST, GET, OPTIONS");
        res.setHeader("Access-Control-Allow-Headers", "Content-Type");
        if (req.method === "OPTIONS") {
          res.writeHead(200);
          res.end();
          return;
        }
        if (req.method === "GET" && req.url === "/status") {
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify({
            connected: this.isConnected(),
            mode: "primary"
          }));
          return;
        }
        if (req.method === "POST" && req.url === "/request") {
          let body = "";
          req.on("data", (chunk) => body += chunk);
          req.on("end", async () => {
            try {
              const { method, params } = JSON.parse(body);
              const result = await this.requestInternal(method, params);
              res.writeHead(200, { "Content-Type": "application/json" });
              res.end(JSON.stringify({ result }));
            } catch (error) {
              res.writeHead(500, { "Content-Type": "application/json" });
              res.end(JSON.stringify({ error: error.message }));
            }
          });
          return;
        }
        res.writeHead(404);
        res.end("Not found");
      });
      const httpPort = this.port + 1;
      this.httpServer.listen(httpPort, () => {
        if (!this.silent) console.error(`[Bridge] HTTP API listening on port ${httpPort}`);
        resolve();
      });
      this.httpServer.on("error", reject);
    });
  }
  /**
   * 停止服务器
   */
  stop() {
    if (this.wss) {
      this.wss.close();
      this.wss = null;
    }
    if (this.httpServer) {
      this.httpServer.close();
      this.httpServer = null;
    }
  }
  /**
   * 检查 Extension 是否已连接
   */
  /**
   * 获取当前运行模式
   */
  getMode() {
    return this.isServerMode ? "primary" : "secondary";
  }
  /**
   * 检查 Extension 是否已连接
   */
  isConnected() {
    if (this.isServerMode) {
      return this.client !== null && this.client.readyState === WS_OPEN;
    } else {
      return false;
    }
  }
  /**
   * 等待 Extension 连接
   */
  waitForConnection(timeoutMs = 6e4) {
    if (this.isServerMode) {
      if (this.client !== null && this.client.readyState === WS_OPEN) {
        return Promise.resolve();
      }
      return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          const index = this.connectionResolvers.indexOf(resolve);
          if (index > -1) {
            this.connectionResolvers.splice(index, 1);
          }
          reject(new Error("timeout"));
        }, timeoutMs);
        this.connectionResolvers.push(() => {
          clearTimeout(timeout);
          resolve();
        });
      });
    } else {
      return new Promise((resolve, reject) => {
        const startTime = Date.now();
        const pollInterval = 2e3;
        let primaryReachable = false;
        let promoting = false;
        const poll = async () => {
          if (Date.now() - startTime > timeoutMs) {
            if (!primaryReachable) {
              reject(new Error("timeout:unreachable"));
            } else {
              reject(new Error("timeout:no_extension"));
            }
            return;
          }
          const health = await this.checkPrimaryHealth();
          if (health.connected) {
            resolve();
            return;
          }
          if (health.error?.includes("not reachable") && !promoting) {
            promoting = true;
            const promoted = await this.tryPromote();
            if (promoted) {
              const remaining = timeoutMs - (Date.now() - startTime);
              if (remaining <= 0) {
                reject(new Error("timeout:no_extension"));
                return;
              }
              if (this.client && this.client.readyState === WS_OPEN) {
                resolve();
                return;
              }
              const promoteTimeout = setTimeout(() => {
                const index = this.connectionResolvers.indexOf(resolve);
                if (index > -1) this.connectionResolvers.splice(index, 1);
                reject(new Error("timeout:no_extension"));
              }, remaining);
              this.connectionResolvers.push(() => {
                clearTimeout(promoteTimeout);
                resolve();
              });
              return;
            }
            promoting = false;
          } else if (!health.error?.includes("not reachable")) {
            primaryReachable = true;
          }
          setTimeout(poll, pollInterval);
        };
        poll();
      });
    }
  }
  /**
   * 检查 Primary 实例健康状态（Secondary 模式用）
   */
  async checkPrimaryHealth() {
    return new Promise((resolve) => {
      const options = {
        hostname: "localhost",
        port: this.port + 1,
        path: "/status",
        method: "GET",
        timeout: 3e3
      };
      const req = http.request(options, (res) => {
        let body = "";
        res.on("data", (chunk) => body += chunk);
        res.on("end", () => {
          try {
            const status = JSON.parse(body);
            resolve({ connected: status.connected });
          } catch {
            resolve({ connected: false, error: "Invalid response from primary" });
          }
        });
      });
      req.on("error", (error) => {
        resolve({ connected: false, error: `Primary not reachable: ${error.message}` });
      });
      req.on("timeout", () => {
        req.destroy();
        resolve({ connected: false, error: "Primary health check timeout" });
      });
      req.end();
    });
  }
  /**
   * 发送请求到 Extension 并等待响应
   */
  async request(method, params) {
    if (this.isServerMode) {
      return this.requestInternal(method, params);
    } else {
      return this.requestViaSecondary(method, params);
    }
  }
  /**
   * SECONDARY 模式请求（带重试 + 自动接管）
   */
  async requestViaSecondary(method, params, maxRetries = 3) {
    let lastError = null;
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      if (this.isServerMode) {
        return this.requestInternal(method, params);
      }
      if (attempt > 0) {
        const delay = Math.min(1e3 * Math.pow(2, attempt - 1), 5e3);
        if (!this.silent) console.error(`[Bridge] SECONDARY retry ${attempt}/${maxRetries} in ${delay}ms...`);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
      const health = await this.checkPrimaryHealth();
      if (!health.connected) {
        if (health.error?.includes("not reachable")) {
          if (!this.silent) console.error("[Bridge] PRIMARY gone during request, attempting takeover...");
          const promoted = await this.tryPromote();
          if (promoted) {
            if (!this.client || this.client.readyState !== WS_OPEN) {
              if (!this.silent) console.error("[Bridge] Waiting for Extension to reconnect...");
              await this.waitForConnection(3e4);
            }
            return this.requestInternal(method, params);
          }
        }
        lastError = new Error(health.error || "Primary instance not available.");
        continue;
      }
      try {
        return await this.requestViaHttp(method, params);
      } catch (error) {
        lastError = error;
      }
    }
    throw lastError;
  }
  /**
   * 尝试接管端口，升级为 PRIMARY
   */
  async tryPromote() {
    for (let i = 0; i < 5; i++) {
      try {
        await this.startServer();
        this.isServerMode = true;
        if (!this.silent) console.error(`[Bridge] Promoted to PRIMARY (WebSocket: ${this.port}, HTTP: ${this.port + 1})`);
        return true;
      } catch {
        await new Promise((r) => setTimeout(r, 1e3));
      }
    }
    return false;
  }
  /**
   * 直接通过 WebSocket 发送请求（服务器模式）
   */
  async requestInternal(method, params) {
    if (!this.client || this.client.readyState !== WS_OPEN) {
      throw new Error("Extension not connected. Please ensure the Chrome extension is running.");
    }
    const id = this.generateId();
    const message = {
      id,
      method,
      token: this.token,
      // 发送 token 供插件端验证
      params
    };
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error(`Request timeout: ${method}`));
      }, this.requestTimeout);
      this.pendingRequests.set(id, { resolve, reject, timeout });
      this.client.send(JSON.stringify(message));
    });
  }
  /**
   * 通过 HTTP API 转发请求（客户端模式）
   */
  requestViaHttp(method, params) {
    return new Promise((resolve, reject) => {
      const data = JSON.stringify({ method, params });
      const options = {
        hostname: "localhost",
        port: this.port + 1,
        path: "/request",
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(data)
        }
      };
      const req = http.request(options, (res) => {
        let body = "";
        res.on("data", (chunk) => body += chunk);
        res.on("end", () => {
          try {
            const response = JSON.parse(body);
            if (response.error) {
              reject(new Error(response.error));
            } else {
              resolve(response.result);
            }
          } catch (error) {
            reject(new Error("Failed to parse response"));
          }
        });
      });
      req.on("error", (error) => {
        const hint = error.message.includes("ECONNREFUSED") ? " (Is the primary MCP server running?)" : "";
        reject(new Error(`Failed to connect to primary MCP instance: ${error.message}${hint}`));
      });
      req.setTimeout(this.requestTimeout, () => {
        req.destroy();
        reject(new Error(`Request timeout: ${method}`));
      });
      req.write(data);
      req.end();
    });
  }
  /**
   * 处理来自 Extension 的消息
   */
  handleMessage(data) {
    try {
      const message = JSON.parse(data);
      const pending = this.pendingRequests.get(message.id);
      if (!pending) {
        console.error("[Bridge] Unknown response id:", message.id);
        return;
      }
      clearTimeout(pending.timeout);
      this.pendingRequests.delete(message.id);
      if (message.error) {
        pending.reject(new Error(message.error.message));
      } else {
        pending.resolve(message.result);
      }
    } catch (error) {
      console.error("[Bridge] Failed to parse message:", error);
    }
  }
  /**
   * 生成唯一 ID
   */
  generateId() {
    return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
  }
  // 分片上传配置
  CHUNK_SIZE = 512 * 1024;
  // 512KB per chunk
  CHUNK_THRESHOLD = 1024 * 1024;
  // 1MB threshold for chunking
  /**
   * 分片上传图片
   * 大于 1MB 的图片会自动分片上传
   */
  async uploadImageChunked(imageData, mimeType, platform = "weibo") {
    if (imageData.length < this.CHUNK_THRESHOLD) {
      return this.request("uploadImage", { imageData, mimeType, platform });
    }
    const uploadId = this.generateId();
    const chunks = [];
    for (let i = 0; i < imageData.length; i += this.CHUNK_SIZE) {
      chunks.push(imageData.slice(i, i + this.CHUNK_SIZE));
    }
    console.error(`[Bridge] Chunked upload: ${chunks.length} chunks, total size: ${imageData.length}`);
    await this.request("uploadImage:start", {
      uploadId,
      totalChunks: chunks.length,
      mimeType,
      platform
    });
    for (let i = 0; i < chunks.length; i++) {
      await this.request("uploadImage:chunk", {
        uploadId,
        chunkIndex: i,
        data: chunks[i]
      });
    }
    const result = await this.request("uploadImage:complete", {
      uploadId
    });
    return result;
  }
};

// src/index.ts
var WS_PORT = parseInt(process.env.SYNC_WS_PORT || "9527", 10);
var HTTP_PORT = parseInt(process.env.SYNC_HTTP_PORT || "9528", 10);
var isSSEMode = process.argv.includes("--sse");
var bridge = new ExtensionBridge(WS_PORT);
function createServer() {
  const server = new Server(
    {
      name: "sync-assistant",
      version: "1.0.0"
    },
    {
      capabilities: {
        tools: {}
      }
    }
  );
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
      tools: [
        {
          name: "list_platforms",
          description: "\u5217\u51FA\u6240\u6709\u652F\u6301\u7684\u5E73\u53F0\u53CA\u5176\u767B\u5F55\u72B6\u6001",
          inputSchema: {
            type: "object",
            properties: {
              forceRefresh: {
                type: "boolean",
                description: "\u662F\u5426\u5F3A\u5236\u5237\u65B0\u767B\u5F55\u72B6\u6001\uFF08\u9ED8\u8BA4\u4F7F\u7528\u7F13\u5B58\uFF09"
              }
            }
          }
        },
        {
          name: "check_auth",
          description: "\u68C0\u67E5\u6307\u5B9A\u5E73\u53F0\u7684\u767B\u5F55\u72B6\u6001",
          inputSchema: {
            type: "object",
            properties: {
              platform: {
                type: "string",
                description: "\u5E73\u53F0 ID\uFF0C\u5982 zhihu, juejin, toutiao \u7B49"
              }
            },
            required: ["platform"]
          }
        },
        {
          name: "sync_article",
          description: "\u540C\u6B65\u6587\u7AE0\u5230\u6307\u5B9A\u5E73\u53F0\uFF08\u4FDD\u5B58\u4E3A\u8349\u7A3F\uFF09\u3002\u652F\u6301 Markdown \u6216 HTML \u683C\u5F0F\uFF0C\u4F18\u5148\u4F7F\u7528 markdown \u5B57\u6BB5\u3002\u91CD\u8981\uFF1A\u5982\u679C\u6587\u7AE0\u5305\u542B\u672C\u5730\u56FE\u7247\u5F15\u7528\uFF0C\u5FC5\u987B\u5148\u8BFB\u53D6\u56FE\u7247\u6587\u4EF6\u5E76\u8F6C\u6362\u4E3A base64 data URI \u683C\u5F0F\uFF08\u5982 ![img](data:image/png;base64,xxx)\uFF09\u3002",
          inputSchema: {
            type: "object",
            properties: {
              platforms: {
                type: "array",
                items: { type: "string" },
                description: '\u76EE\u6807\u5E73\u53F0 ID \u5217\u8868\uFF0C\u5982 ["zhihu", "juejin"]'
              },
              title: {
                type: "string",
                description: "\u6587\u7AE0\u6807\u9898\uFF08\u7EAF\u6587\u672C\uFF0C\u4E0D\u542B # \u53F7\uFF09"
              },
              markdown: {
                type: "string",
                description: "\u6587\u7AE0\u6B63\u6587\u5185\u5BB9\uFF08Markdown \u683C\u5F0F\uFF0C\u63A8\u8350\uFF09\u3002\u6CE8\u610F\uFF1A1) \u4E0D\u8981\u5305\u542B\u6807\u9898\u884C\uFF08# xxx\uFF09\uFF0C\u53EA\u4F20\u6B63\u6587\u90E8\u5206\uFF1B2) \u672C\u5730\u56FE\u7247\u5FC5\u987B\u8F6C\u6362\u4E3A base64 data URI \u683C\u5F0F\uFF0C\u5982 ![\u56FE\u7247](data:image/png;base64,iVBORw0KGgo...)"
              },
              content: {
                type: "string",
                description: "\u6587\u7AE0\u6B63\u6587\u5185\u5BB9\uFF08HTML \u683C\u5F0F\uFF0C\u53EF\u9009\uFF09\u3002\u5982\u679C\u63D0\u4F9B\u4E86 markdown \u5219\u6B64\u5B57\u6BB5\u53EF\u5FFD\u7565\u3002"
              },
              cover: {
                type: "string",
                description: "\u5C01\u9762\u56FE URL \u6216 base64 data URI\uFF08\u53EF\u9009\uFF09"
              }
            },
            required: ["platforms", "title", "markdown"]
          }
        },
        {
          name: "extract_article",
          description: "\u4ECE\u5F53\u524D\u6D4F\u89C8\u5668\u9875\u9762\u63D0\u53D6\u6587\u7AE0\u5185\u5BB9",
          inputSchema: {
            type: "object",
            properties: {}
          }
        },
        {
          name: "upload_image_file",
          description: "\u4ECE\u672C\u5730\u6587\u4EF6\u8DEF\u5F84\u4E0A\u4F20\u56FE\u7247\u5230\u56FE\u5E8A\u5E73\u53F0\uFF0C\u8FD4\u56DE\u53EF\u516C\u5F00\u8BBF\u95EE\u7684 URL\u3002\u63A8\u8350\u4F7F\u7528\u6B64\u65B9\u6CD5\uFF0C\u65E0\u9700\u624B\u52A8\u8F6C\u6362 base64\u3002",
          inputSchema: {
            type: "object",
            properties: {
              filePath: {
                type: "string",
                description: "\u672C\u5730\u56FE\u7247\u6587\u4EF6\u7684\u7EDD\u5BF9\u8DEF\u5F84\uFF0C\u5982 /Users/xxx/image.png"
              },
              platform: {
                type: "string",
                description: "\u4E0A\u4F20\u5230\u54EA\u4E2A\u5E73\u53F0\u4F5C\u4E3A\u56FE\u5E8A\uFF0C\u9ED8\u8BA4 weibo\u3002\u53EF\u9009: weibo, zhihu, juejin, jianshu, woshipm"
              }
            },
            required: ["filePath"]
          }
        }
      ]
    };
  });
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    try {
      if (!bridge.isConnected()) {
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                error: "Chrome Extension \u672A\u8FDE\u63A5\u3002\u8BF7\u786E\u4FDD\uFF1A\n1. \u5DF2\u5B89\u88C5\u540C\u6B65\u52A9\u624B\u6269\u5C55\n2. \u6269\u5C55\u5DF2\u542F\u7528 MCP \u8FDE\u63A5\uFF08\u70B9\u51FB\u8BBE\u7F6E\u56FE\u6807\u5F00\u542F\uFF09"
              })
            }
          ],
          isError: true
        };
      }
      let result;
      switch (name) {
        case "list_platforms":
          result = await bridge.request("listPlatforms", {
            forceRefresh: args?.forceRefresh
          });
          break;
        case "check_auth":
          result = await bridge.request("checkAuth", {
            platform: args.platform
          });
          break;
        case "sync_article":
          result = await bridge.request("syncArticle", {
            platforms: args.platforms,
            article: {
              title: args.title,
              content: args.content,
              markdown: args.markdown,
              cover: args.cover
            }
          });
          break;
        case "extract_article":
          result = await bridge.request("extractArticle");
          break;
        case "upload_image_file": {
          const filePath = args.filePath;
          const platform = args.platform || "weibo";
          if (!fs.existsSync(filePath)) {
            throw new Error(`File not found: ${filePath}`);
          }
          const fileBuffer = fs.readFileSync(filePath);
          const imageData = fileBuffer.toString("base64");
          const ext = path.extname(filePath).toLowerCase();
          const mimeTypes = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".svg": "image/svg+xml"
          };
          const mimeType = mimeTypes[ext] || "image/png";
          result = await bridge.uploadImageChunked(imageData, mimeType, platform);
          break;
        }
        default:
          return {
            content: [{ type: "text", text: `Unknown tool: ${name}` }],
            isError: true
          };
      }
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result, null, 2)
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({ error: error.message })
          }
        ],
        isError: true
      };
    }
  });
  return server;
}
async function startStdioMode() {
  await bridge.start();
  const server = createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[MCP] Sync Assistant started (stdio mode)");
  console.error(`[MCP] Extension WebSocket: ws://localhost:${WS_PORT}`);
}
async function startSSEMode() {
  await bridge.start();
  const server = createServer();
  const app = express();
  let transport = null;
  app.get("/sse", async (req, res) => {
    console.error("[MCP] New SSE connection from Claude Code");
    transport = new SSEServerTransport("/message", res);
    res.on("close", () => {
      console.error("[MCP] SSE connection closed");
      transport = null;
    });
    await server.connect(transport);
  });
  app.post("/message", express.json(), async (req, res) => {
    if (transport) {
      await transport.handlePostMessage(req, res);
    } else {
      res.status(400).json({ error: "No active SSE connection" });
    }
  });
  app.get("/health", (_req, res) => {
    res.json({
      status: "ok",
      extensionConnected: bridge.isConnected()
    });
  });
  app.get("/", (_req, res) => {
    res.json({
      name: "Sync Assistant MCP Server",
      version: "1.0.0",
      extensionConnected: bridge.isConnected()
    });
  });
  app.listen(HTTP_PORT, () => {
    console.error("[MCP] Sync Assistant started (SSE mode)");
    console.error(`[MCP] HTTP Server: http://localhost:${HTTP_PORT}`);
    console.error(`[MCP] Claude Code: http://localhost:${HTTP_PORT}/sse`);
    console.error(`[MCP] Extension WebSocket: ws://localhost:${WS_PORT}`);
  });
}
if (isSSEMode) {
  startSSEMode().catch((error) => {
    console.error("[MCP] Failed to start:", error);
    process.exit(1);
  });
} else {
  startStdioMode().catch((error) => {
    console.error("[MCP] Failed to start:", error);
    process.exit(1);
  });
}
process.on("SIGINT", () => {
  console.error("[MCP] Shutting down...");
  process.exit(0);
});
process.on("SIGTERM", () => {
  console.error("[MCP] Shutting down...");
  process.exit(0);
});
//# sourceMappingURL=index.js.map