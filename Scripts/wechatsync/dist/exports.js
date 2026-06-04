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
export {
  ExtensionBridge
};
//# sourceMappingURL=exports.js.map