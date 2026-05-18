#!/usr/bin/env python3
"""
飞书多维表格操作工具 — ContentFleet 集成
使用 lark-oapi SDK 或直接 HTTP 调用飞书 OpenAPI
"""

import json
import sys
import os
import urllib.request
import urllib.parse
import ssl

# ── 配置 ──────────────────────────────────────────────
APP_ID = os.environ.get("LARK_APP_ID", "cli_a93af46f79389cc4")
APP_SECRET = os.environ.get("LARK_APP_SECRET", "mBrSJIZPUPTG5KfZ605ybgo7TxMNOdac")
BITABLE_APP_TOKEN = "CFF5boINWaBpb4sqlFVceacEn5c"  # 从你的飞书链接中提取
BASE_URL = "https://open.feishu.cn"

# 已知表 ID（2026-05-17 从 API 获取）
TABLE_ARTICLE = "tblA8dT3x3bdOF9Y"   # 文章追踪
TABLE_TOPIC = "tblx7PYNPRVBHGET"     # 选题库v2

# SSL context (忽略证书验证以绕过网络限制)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def _request(method, path, data=None, token=None):
    """统一 HTTP 请求封装"""
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        return {"code": e.code, "msg": f"HTTP {e.code}", "error": error_body}
    except Exception as e:
        return {"code": -1, "msg": str(e)}


def get_tenant_token():
    """获取 tenant_access_token"""
    resp = _request("POST", "/open-apis/auth/v3/tenant_access_token/internal", {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    })
    if resp.get("code") == 0:
        return resp["tenant_access_token"]
    else:
        print(f"❌ 获取 token 失败: {resp}", file=sys.stderr)
        return None


def list_tables(token):
    """列出 Bitable 中所有数据表"""
    resp = _request("GET", f"/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables", token=token)
    if resp.get("code") == 0:
        tables = resp["data"]["items"]
        print(f"\n📊 共 {len(tables)} 张数据表：")
        for t in tables:
            print(f"  • {t['name']} (table_id: {t['table_id']})")
        return tables
    else:
        print(f"❌ 列表失败: {resp}")
        return []


def list_fields(token, table_id):
    """列出某张表的所有字段"""
    resp = _request("GET", 
        f"/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{table_id}/fields",
        token=token)
    if resp.get("code") == 0:
        fields = resp["data"]["items"]
        print(f"\n📋 字段列表 (共 {len(fields)} 个)：")
        type_map = {
            1: "文本", 2: "数字", 3: "单选", 4: "多选", 5: "日期",
            7: "复选框", 11: "人员", 13: "电话", 15: "URL", 17: "附件",
            18: "关联", 19: "查找引用", 20: "公式", 21: "自动编号",
            22: "创建时间", 23: "修改时间", 1001: "创建人", 1002: "修改人"
        }
        for f in fields:
            ftype = type_map.get(f.get("type", 0), f"type={f.get('type')}")
            print(f"  • {f['field_name']:20s} | {ftype:8s} | field_id: {f['field_id']}")
        return fields
    else:
        print(f"❌ 字段列表失败: {resp}")
        return []


def list_records(token, table_id, page_size=20, page_token=None):
    """列出某张表的记录"""
    params = f"page_size={page_size}"
    if page_token:
        params += f"&page_token={page_token}"
    resp = _request("GET",
        f"/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{table_id}/records?{params}",
        token=token)
    if resp.get("code") == 0:
        data = resp["data"]
        records = data.get("items", [])
        total = data.get("total", 0)
        has_more = data.get("has_more", False)
        print(f"\n📝 记录 (总计 {total} 条, 本页 {len(records)} 条)：")
        for r in records[:5]:  # 只显示前5条
            fields = r.get("fields", {})
            preview = {k: str(v)[:50] for k, v in list(fields.items())[:6]}
            print(f"  {json.dumps(preview, ensure_ascii=False)}")
        if len(records) > 5:
            print(f"  ... 还有 {len(records) - 5} 条")
        return records, has_more, data.get("page_token")
    else:
        print(f"❌ 记录列表失败: {resp}")
        return [], False, None


def create_field(token, table_id, field_name, field_type, description="", options=None):
    """在表中新增字段
    field_type: 1=文本 2=数字 3=单选 4=多选 5=日期 7=复选框 15=URL 20=公式
    """
    body = {
        "field_name": field_name,
        "type": field_type
    }
    if description:
        body["description"] = {"text": description}
    if options and field_type in (3, 4):  # 单选/多选
        body["property"] = {"options": [{"name": o} for o in options]}
    
    resp = _request("POST",
        f"/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{table_id}/fields",
        data=body, token=token)
    if resp.get("code") == 0:
        print(f"  ✅ 字段 '{field_name}' 创建成功")
        return resp["data"]["field"]
    else:
        print(f"  ❌ 字段 '{field_name}' 创建失败: {resp.get('msg', resp)}")
        return None


def create_record(token, table_id, fields_data):
    """新增一条记录"""
    resp = _request("POST",
        f"/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{table_id}/records",
        data={"fields": fields_data}, token=token)
    if resp.get("code") == 0:
        return resp["data"]["record"]
    else:
        print(f"  ❌ 记录创建失败: {resp.get('msg', resp)}")
        return None


def batch_create_records(token, table_id, records_list):
    """批量新增记录"""
    body = {"records": [{"fields": r} for r in records_list]}
    resp = _request("POST",
        f"/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{table_id}/records/batch_create",
        data=body, token=token)
    if resp.get("code") == 0:
        created = resp["data"].get("records", [])
        print(f"  ✅ 批量创建 {len(created)} 条记录")
        return created
    else:
        print(f"  ❌ 批量创建失败: {resp.get('msg', resp)}")
        return []


def create_table(token, table_name, fields_spec):
    """在 Bitable 中新建数据表
    fields_spec: [{"field_name": "xxx", "type": 1}, ...]
    """
    body = {
        "table": {
            "name": table_name,
            "default_view_name": "Grid View",
            "fields": fields_spec
        }
    }
    resp = _request("POST",
        f"/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables",
        data=body, token=token)
    if resp.get("code") == 0:
        table_id = resp["data"]["table_id"]
        print(f"✅ 表 '{table_name}' 创建成功 (table_id: {table_id})")
        return table_id
    else:
        print(f"❌ 表 '{table_name}' 创建失败: {resp.get('msg', resp)}")
        return None


# ── 主入口 ──────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("""
飞书多维表格操作工具 — ContentFleet 集成
用法:
  python3 feishu_ops.py inspect          # 查看所有表 + 字段结构
  python3 feishu_ops.py records <table_id>  # 查看某表记录
  python3 feishu_ops.py upgrade-article  # 升级「文章追踪」表（新增缺失字段）
  python3 feishu_ops.py token            # 仅获取并打印 token
        """)
        return
    
    cmd = sys.argv[1]
    
    if cmd == "token":
        token = get_tenant_token()
        if token:
            print(f"✅ tenant_access_token: {token}")
        return
    
    token = get_tenant_token()
    if not token:
        print("❌ 无法获取 token，请检查 App ID / Secret")
        return
    
    if cmd == "inspect":
        tables = list_tables(token)
        for t in tables:
            print(f"\n{'='*60}")
            print(f"📊 表: {t['name']}")
            print(f"{'='*60}")
            list_fields(token, t["table_id"])
            records, _, _ = list_records(token, t["table_id"], page_size=5)
    
    elif cmd == "records":
        table_id = sys.argv[2] if len(sys.argv) > 2 else None
        if not table_id:
            print("用法: python3 feishu_ops.py records <table_id>")
            return
        list_records(token, table_id, page_size=50)
    
    elif cmd == "upgrade-article":
        # 升级文章追踪表：新增 ContentFleet 需要的字段
        tables = list_tables(token)
        article_table = None
        for t in tables:
            if "文章追踪" in t["name"]:
                article_table = t
                break
        
        if not article_table:
            print("❌ 找不到「文章追踪」表")
            return
        
        table_id = article_table["table_id"]
        existing = list_fields(token, table_id)
        existing_names = {f["field_name"] for f in existing}
        
        # 定义需要新增的字段
        new_fields = [
            ("文章标题", 1, "终稿标题（≤30字）"),
            ("文章类型", 3, "选购横评/教程避坑/趋势科普", ["选购横评", "教程避坑", "趋势科普"]),
            ("展现量", 2, "头条后台展现量"),
            ("CTR(%)", 2, "点击率 = 阅读量/展现量"),
            ("完读率(%)", 2, "完读率百分比"),
            ("平均阅读时长(s)", 2, "秒数"),
            ("评论数", 2, ""),
            ("收藏数", 2, ""),
            ("标题结构模板", 3, "高表现标题模板分类",
             ["内幕视角型", "反问悬念型", "对比选择型", "品牌锚点型", "内幕避坑型", "多品牌对决型", "其他"]),
            ("是否限流", 3, "限流状态", ["正常", "疑似限流", "确认限流"]),
            ("限流原因", 1, "如有限流，具体原因"),
            ("标题字数", 2, "标题长度"),
            ("当前阶段", 3, "T1-T7 流水线状态",
             ["T1选题", "T2调研", "T3写作", "T4审查", "T5配图", "T6终稿", "T7归档", "已发布"]),
            ("T4驳回次数", 2, "0/1/2/3"),
            ("驳回原因", 1, ""),
            ("复盘评分", 2, "1-5分"),
            ("复盘关键教训", 1, ""),
            ("归档路径", 1, "Google Drive 项目文件夹路径"),
            ("字数", 2, "终稿字数"),
        ]
        
        print(f"\n🔧 升级「文章追踪」表，检查 {len(new_fields)} 个字段...")
        added = 0
        for spec in new_fields:
            name = spec[0]
            if name in existing_names:
                print(f"  ⏭️  '{name}' 已存在，跳过")
                continue
            ftype = spec[1]
            desc = spec[2] if len(spec) > 2 else ""
            options = spec[3] if len(spec) > 3 else None
            result = create_field(token, table_id, name, ftype, desc, options)
            if result:
                added += 1
        
        print(f"\n✅ 升级完成：新增 {added} 个字段")
    
    else:
        print(f"未知命令: {cmd}")


if __name__ == "__main__":
    main()
