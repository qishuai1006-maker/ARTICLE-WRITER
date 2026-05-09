/**
 * ContentFleet MCP Server · 产品信息库 + 抖音 + Tavily
 * =====================================================
 * 把三个外部 API 封装为 Claude Code 原生工具，Agent 直接调用工具名即可。
 *
 * 工具列表:
 *   产品信息库:
 *     - product_structure  获取品类参数结构
 *     - product_search     搜索产品（内置三级降级策略）
 *     - product_add        提交京东链接入库
 *
 *   抖音:
 *     - douyin_search      作品搜索（按互动量排序）
 *     - douyin_list        达人作品列表
 *     - douyin_item        作品详情
 *     - douyin_add         达人添加
 *
 *   Tavily:
 *     - tavily_search      高级搜索
 *
 *   辅助:
 *     - pinlei_list        品类标识速查表
 *
 * 启动: node Scripts/mcp/server.mjs
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

// ============================================================
// 配置
// ============================================================

const CLAW_API_KEY =
  process.env.CLAW_API_KEY ||
  "718af82b5941ddc5f0f3606683554077599e79169dc3dc2a";
const TAVILY_API_KEY =
  process.env.TAVILY_API_KEY ||
  "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";

const CLAW_BASE = "http://clawapi.ltnwl.com";
const TAVILY_BASE = "https://api.tavily.com";

// 请求超时（毫秒）
const TIMEOUT_MS = 15000;

// 简易缓存（key → { data, ts }）
const cache = new Map();
const CACHE_TTL_MS = 10 * 60 * 1000; // 10 分钟

// 品类标识速查表
const PINLEI_MAP = {
  冰箱: "bingxiang",
  空调: "kongtiao",
  滚筒洗衣机: "xiyiji",
  洗衣机: "xiyiji",
  波轮洗衣机: "bolunxi",
  波轮: "bolunxi",
  电视: "dianshi",
  投影仪: "touyingyi",
  烟灶: "yanzao",
  集成灶: "jichengzao",
  燃气热水器: "ranqireshuiqi",
  燃热: "ranqireshuiqi",
  电热水器: "dianreshuiqi",
  电热: "dianreshuiqi",
  洗碗机: "xiwanji",
  蒸烤箱: "zhengkaoxiang",
  智能锁: "zhinengsuo",
  智能马桶: "zhinengmatong",
  洗地机: "xidiji",
  扫地机: "saodiji",
  净水器: "jingshuiqi",
  净水: "jingshuiqi",
  管线机: "guanxianji",
  床垫: "chuangdian",
  花洒: "huasha",
  干衣机: "ganyiji",
  新风机: "xinfengji",
  空气净化器: "kongqijinghuaqi",
  加湿器: "jiashiqi",
  除湿机: "chushiji",
};

// ============================================================
// HTTP 工具函数
// ============================================================

async function fetchWithTimeout(url, options = {}, timeoutMs = TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const resp = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timer);
    return resp;
  } catch (err) {
    clearTimeout(timer);
    if (err.name === "AbortError") {
      throw new Error(`请求超时 (${timeoutMs}ms): ${url}`);
    }
    throw err;
  }
}

async function postForm(url, params) {
  const body = new URLSearchParams(params);
  const resp = await fetchWithTimeout(url, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });
  return resp.json();
}

async function postJSON(url, data) {
  const resp = await fetchWithTimeout(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return resp.json();
}

function getCached(key) {
  const entry = cache.get(key);
  if (entry && Date.now() - entry.ts < CACHE_TTL_MS) {
    return entry.data;
  }
  cache.delete(key);
  return null;
}

function setCache(key, data) {
  cache.set(key, { data, ts: Date.now() });
}

function textResult(text) {
  return { content: [{ type: "text", text }] };
}

function jsonResult(data) {
  return textResult(JSON.stringify(data, null, 2));
}

// ============================================================
// MCP Server 创建
// ============================================================

const server = new McpServer({
  name: "contentfleet-api",
  version: "1.0.0",
});

// ============================================================
// 工具 1: 品类标识速查
// ============================================================

server.tool(
  "pinlei_list",
  "品类标识速查表。返回所有支持的品类中文名和对应的 pinlei 标识符。在调用产品信息库前先查此表确认品类标识。",
  {},
  async () => {
    const rows = Object.entries(PINLEI_MAP)
      .map(([cn, code]) => `  ${cn} → ${code}`)
      .join("\n");
    return textResult(`支持的品类（共 ${Object.keys(PINLEI_MAP).length} 个）:\n${rows}`);
  }
);

// ============================================================
// 工具 2: product_structure — 获取品类参数结构
// ============================================================

server.tool(
  "product_structure",
  "获取指定品类的参数结构定义。返回该品类有哪些参数字段、字段含义。在搜索产品前先调用此工具了解数据结构。",
  {
    pinlei: z
      .string()
      .describe(
        "品类标识（如 bingxiang/kongtiao/xiyiji）。可先调用 pinlei_list 查询。"
      ),
  },
  async ({ pinlei }) => {
    const cacheKey = `structure:${pinlei}`;
    const cached = getCached(cacheKey);
    if (cached) return jsonResult({ ...cached, _cached: true });

    try {
      const data = await postForm(`${CLAW_BASE}/product/structure/`, {
        api_key: CLAW_API_KEY,
        pinlei,
      });
      setCache(cacheKey, data);
      return jsonResult(data);
    } catch (err) {
      return textResult(`❌ 产品结构查询失败: ${err.message}`);
    }
  }
);

// ============================================================
// 工具 3: product_search — 产品搜索（内置三级降级）
// ============================================================

server.tool(
  "product_search",
  `搜索产品信息库。内置三级降级策略：
1. keyword 精确搜索（型号/产品名）
2. brand 品牌搜索（如 keyword 无结果）
3. pinlei 品类搜索（最宽泛）

返回产品列表含：名称、型号、品牌、参数、价格、推荐等级、点评。`,
  {
    pinlei: z.string().describe("品类标识（必填，如 bingxiang/kongtiao）"),
    keyword: z
      .string()
      .optional()
      .describe("搜索关键词（型号或产品名，如 '海尔BCD-510'）"),
    brand: z
      .string()
      .optional()
      .describe("品牌名（如 '海尔'/'美的'，降级搜索时使用）"),
    tjnum: z
      .string()
      .optional()
      .default("5,4")
      .describe("推荐等级筛选（5,4 = 仅4星和5星）"),
    pagesize: z
      .number()
      .optional()
      .default(20)
      .describe("返回数量（默认20）"),
  },
  async ({ pinlei, keyword, brand, tjnum, pagesize }) => {
    const params = {
      api_key: CLAW_API_KEY,
      pinlei,
      tjnum: tjnum || "5,4",
      pagesize: String(pagesize || 20),
    };

    // 三级降级策略
    const strategies = [];
    if (keyword) strategies.push({ level: "keyword", params: { ...params, keyword } });
    if (brand) strategies.push({ level: "brand", params: { ...params, brand } });
    strategies.push({ level: "pinlei", params });

    for (const strategy of strategies) {
      const cacheKey = `search:${JSON.stringify(strategy.params)}`;
      const cached = getCached(cacheKey);
      if (cached) {
        return jsonResult({
          _search_level: strategy.level,
          _cached: true,
          ...cached,
        });
      }

      try {
        const data = await postForm(
          `${CLAW_BASE}/product/search/`,
          strategy.params
        );

        // 检查是否有结果
        const hasResults =
          data &&
          ((Array.isArray(data.data) && data.data.length > 0) ||
            (data.total && data.total > 0) ||
            (typeof data === "object" && !data.error));

        if (hasResults) {
          setCache(cacheKey, data);
          return jsonResult({
            _search_level: strategy.level,
            _note:
              strategy.level !== "keyword"
                ? `⚠️ 通过${strategy.level}级降级搜索获得结果`
                : "精确匹配",
            ...data,
          });
        }
        // 无结果，继续降级
      } catch (err) {
        // 该级别失败，继续降级
        continue;
      }
    }

    return textResult(
      `❌ 产品搜索无结果（三级降级全部尝试）\n品类: ${pinlei}\n关键词: ${keyword || "无"}\n品牌: ${brand || "无"}\n建议: 尝试更换关键词，或用 product_add 提交京东链接入库`
    );
  }
);

// ============================================================
// 工具 4: product_add — 提交京东链接入库
// ============================================================

server.tool(
  "product_add",
  "提交京东商品链接到产品信息库。用于库中查不到的产品，提交后系统自动抓取参数入库。",
  {
    url: z.string().describe("京东商品链接（如 https://item.jd.com/100012345.html）"),
    pinlei: z.string().describe("品类标识"),
  },
  async ({ url, pinlei }) => {
    try {
      const data = await postForm(`${CLAW_BASE}/product/add/`, {
        api_key: CLAW_API_KEY,
        url,
        pinlei,
      });
      return jsonResult(data);
    } catch (err) {
      return textResult(`❌ 产品添加失败: ${err.message}`);
    }
  }
);

// ============================================================
// 工具 5: douyin_search — 抖音作品搜索
// ============================================================

server.tool(
  "douyin_search",
  `搜索抖音作品（按互动量排序，含完整文案）。
⚠️ 关键词规则：只传核心产品关键词，用空格分隔，去掉修饰词（爆款/推荐/热门/最好等）。
示例：「零冷水燃气热水器推荐」→ keyword="零冷水 燃气 热水器"
仅支持家电/家装/家居类目。`,
  {
    keyword: z
      .string()
      .describe(
        "搜索关键词（只传核心产品词，空格分隔，去掉修饰词）"
      ),
    search_type: z
      .number()
      .optional()
      .default(1)
      .describe("搜索类型（0=综合, 1=视频，默认1）"),
  },
  async ({ keyword, search_type }) => {
    const cacheKey = `douyin_search:${keyword}:${search_type}`;
    const cached = getCached(cacheKey);
    if (cached) return jsonResult({ ...cached, _cached: true });

    try {
      const data = await postForm(`${CLAW_BASE}/douyin/douyin_search/`, {
        api_key: CLAW_API_KEY,
        keyword,
        search_type: String(search_type || 1),
      });
      setCache(cacheKey, data);
      return jsonResult(data);
    } catch (err) {
      return textResult(
        `❌ 抖音搜索失败: ${err.message}\n建议: 检查关键词是否为家电/家装/家居类目`
      );
    }
  }
);

// ============================================================
// 工具 6: douyin_list — 达人作品列表
// ============================================================

server.tool(
  "douyin_list",
  "获取指定抖音达人的作品列表（含文案）。用于分析 TOP 达人的内容方向。",
  {
    dr_name: z.string().describe("达人昵称"),
  },
  async ({ dr_name }) => {
    const cacheKey = `douyin_list:${dr_name}`;
    const cached = getCached(cacheKey);
    if (cached) return jsonResult({ ...cached, _cached: true });

    try {
      const data = await postForm(`${CLAW_BASE}/douyin/douyin_list/`, {
        api_key: CLAW_API_KEY,
        dr_name,
      });
      setCache(cacheKey, data);
      return jsonResult(data);
    } catch (err) {
      if (err.message.includes("404")) {
        return textResult(
          `❌ 达人「${dr_name}」未收录。可调用 douyin_add 提交收录请求。`
        );
      }
      return textResult(`❌ 抖音达人作品查询失败: ${err.message}`);
    }
  }
);

// ============================================================
// 工具 7: douyin_item — 作品详情
// ============================================================

server.tool(
  "douyin_item",
  "获取单个抖音作品的详细信息（仅用于趋势分析，不作为正文引述来源）。",
  {
    zpid: z.string().describe("作品ID"),
  },
  async ({ zpid }) => {
    try {
      const data = await postForm(`${CLAW_BASE}/douyin/douyin_item/`, {
        api_key: CLAW_API_KEY,
        zpid,
      });
      return jsonResult(data);
    } catch (err) {
      return textResult(`❌ 抖音作品详情查询失败: ${err.message}`);
    }
  }
);

// ============================================================
// 工具 8: douyin_add — 达人添加
// ============================================================

server.tool(
  "douyin_add",
  "提交抖音达人收录请求。当 douyin_search 或 douyin_list 查不到数据时调用。",
  {
    name: z.string().describe("达人昵称"),
  },
  async ({ name }) => {
    try {
      const data = await postForm(`${CLAW_BASE}/douyin/douyin_add/`, {
        api_key: CLAW_API_KEY,
        name,
      });
      return jsonResult(data);
    } catch (err) {
      return textResult(`❌ 达人添加失败: ${err.message}`);
    }
  }
);

// ============================================================
// 工具 9: tavily_search — Tavily 高级搜索
// ============================================================

server.tool(
  "tavily_search",
  `使用 Tavily API 进行高级网络搜索。返回相关网页的标题、URL、摘要内容。
用于：实时数据验证、最新评测查找、市场动态、用户口碑收集。
与产品信息库互补使用，实现双源交叉验证。`,
  {
    query: z.string().describe("搜索查询词"),
    max_results: z
      .number()
      .optional()
      .default(5)
      .describe("最大返回结果数（默认5）"),
    search_depth: z
      .enum(["basic", "advanced"])
      .optional()
      .default("advanced")
      .describe("搜索深度（basic=快速, advanced=深度，默认 advanced）"),
  },
  async ({ query, max_results, search_depth }) => {
    const cacheKey = `tavily:${query}:${max_results}:${search_depth}`;
    const cached = getCached(cacheKey);
    if (cached) return jsonResult({ ...cached, _cached: true });

    try {
      const data = await postJSON(`${TAVILY_BASE}/search`, {
        api_key: TAVILY_API_KEY,
        query,
        search_depth: search_depth || "advanced",
        max_results: max_results || 5,
      });
      setCache(cacheKey, data);
      return jsonResult(data);
    } catch (err) {
      if (err.message.includes("401")) {
        return textResult(
          `❌ Tavily API 认证失败 (401)。可能是 API Key 过期或额度用完。\n降级建议: 此次搜索跳过 Tavily，使用产品信息库 + WebSearch 作为替代。`
        );
      }
      return textResult(`❌ Tavily 搜索失败: ${err.message}`);
    }
  }
);

// ============================================================
// 启动
// ============================================================

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error("MCP Server 启动失败:", err);
  process.exit(1);
});
