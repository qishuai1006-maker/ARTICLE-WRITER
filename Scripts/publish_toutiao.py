#!/usr/bin/env python3
"""
ContentFleet v6.0 · 头条自动发布脚本（publish_toutiao.py）
=========================================================
用法:
  python3 Scripts/publish_toutiao.py outputs/T6_final_头条.md [--publish] [--debug]

前置条件:
  1. Chrome 以远程调试模式启动:
     /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
  2. 在 Chrome 中已登录 mp.toutiao.com（头条号创作中心）
  3. Playwright 已安装: pip install playwright && playwright install chromium

工作模式:
  默认 dry_run 模式（预览 + 人工确认）
  --publish  自动点击发布按钮
  --debug    打印调试信息，不关闭浏览器

流程:
  T6 终稿 → 解析标题/正文/配图/标签
          → Playwright 连接已有 Chrome
          → 导航到创作中心发布页
          → 填写标题 + 粘贴正文 + 上传配图
          → dry_run: 暂停等待人工确认
          → --publish: 自动点击发布
"""

import re
import sys
import time
import json
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ 需要安装 Playwright: pip install playwright && playwright install chromium")
    sys.exit(1)


# ============================================================
# Markdown 解析
# ============================================================

def parse_t6_article(md_path: str) -> dict:
    """
    解析 T6 终稿 Markdown 文件，提取发布所需的结构化数据。
    返回: { title, body_html, images, tags, cover_image }
    """
    content = Path(md_path).read_text("utf-8")
    lines = content.split("\n")

    # 提取标题（第一个 # 开头的行）
    title = ""
    title_line_idx = -1
    for idx, line in enumerate(lines):
        if line.startswith("# ") and not line.startswith("## "):
            title = line.lstrip("# ").strip()
            title_line_idx = idx
            break

    if not title:
        print("⚠️  未找到 H1 标题，使用文件名作为标题")
        title = Path(md_path).stem.replace("T6_final_", "")

    # 标题长度检查
    if len(title) > 30:
        print(f"⚠️  标题超长({len(title)}字)，将截断到30字: {title[:30]}...")
        title = title[:30]

    # 提取图片路径（相对路径转绝对路径）
    images = []
    md_dir = Path(md_path).parent.resolve()
    for match in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', content):
        alt_text = match.group(1)
        img_path = match.group(2)
        # 处理相对路径
        if not img_path.startswith("/"):
            img_full = md_dir / img_path
        else:
            img_full = Path(img_path)
        if img_full.exists():
            images.append({
                "alt": alt_text,
                "path": str(img_full.resolve()),
                "name": img_full.name,
            })
        else:
            print(f"⚠️  图片不存在: {img_path}")

    # 识别封面图（优先 T5_封面图.png）
    cover_image = None
    for img in images:
        if "封面" in img["name"]:
            cover_image = img["path"]
            break
    if not cover_image and images:
        cover_image = images[0]["path"]

    # 提取标签（从元数据或文末提取）
    tags = []
    tag_patterns = [
        r'tags?[:：]\s*(.+)',
        r'标签[:：]\s*(.+)',
        r'话题[:：]\s*(.+)',
    ]
    for pattern in tag_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            raw_tags = match.group(1)
            tags = [t.strip().strip("#") for t in re.split(r'[,，、\s#]+', raw_tags) if t.strip()]
            break

    # 正文处理：去掉标题行和元数据，保留正文
    body_lines = []
    in_metadata = False
    for idx, line in enumerate(lines):
        if idx == title_line_idx:
            continue
        if line.strip() == "---":
            in_metadata = not in_metadata
            continue
        if in_metadata:
            continue
        # 跳过标签行
        if any(re.match(p, line, re.I) for p in tag_patterns):
            continue
        body_lines.append(line)

    body_text = "\n".join(body_lines).strip()

    return {
        "title": title,
        "body": body_text,
        "images": images,
        "tags": tags,
        "cover_image": cover_image,
    }


# ============================================================
# Markdown → 头条富文本转换
# ============================================================

def md_to_toutiao_text(md_text: str) -> str:
    """
    将 Markdown 正文转换为适合粘贴到头条编辑器的纯文本。
    头条编辑器支持基础富文本，但通过剪贴板粘贴时最可靠的是纯文本 + 手动格式。
    """
    text = md_text

    # 移除图片标记（图片单独上传）
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'[图片: \1]', text)

    # 移除链接，保留文字
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # 加粗 → 保留文字（头条编辑器粘贴不支持 Markdown 加粗）
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)

    # 表格简化处理
    # 保留表格内容但去掉分隔行
    text = re.sub(r'\|[-:]+\|[-:|\s]+\|?\n', '', text)

    # 标题降级为加粗文本样式
    text = re.sub(r'^#{2,6}\s+(.+)$', r'【\1】', text, flags=re.MULTILINE)

    # 清理多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


# ============================================================
# 浏览器自动化
# ============================================================

def connect_to_chrome(debug_port: int = 9222):
    """连接已打开的 Chrome 浏览器"""
    try:
        p = sync_playwright().start()
        browser = p.chromium.connect_over_cdp(f"http://localhost:{debug_port}")
        print(f"✅ 已连接到 Chrome (port {debug_port})")
        return p, browser
    except Exception as e:
        print(f"❌ 无法连接到 Chrome: {e}")
        print(f"   请确保 Chrome 以远程调试模式启动:")
        print(f"   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port={debug_port}")
        sys.exit(1)


def check_login_status(page) -> bool:
    """检查是否已登录头条号"""
    page.goto("https://mp.toutiao.com/profile_v4/graphic/publish", wait_until="networkidle", timeout=15000)
    time.sleep(2)

    # 检查是否被重定向到登录页
    current_url = page.url
    if "login" in current_url or "sso" in current_url:
        print("❌ 未登录头条号，请先在 Chrome 中登录 mp.toutiao.com")
        return False

    print("✅ 头条号已登录")
    return True


def fill_title(page, title: str):
    """填写文章标题"""
    # 头条创作中心的标题输入框选择器（可能需要根据实际页面调整）
    title_selectors = [
        'textarea[placeholder*="标题"]',
        'input[placeholder*="标题"]',
        '.title-input textarea',
        '.title-input input',
        '[data-testid="title-input"]',
        'textarea.article-title',
    ]

    for selector in title_selectors:
        try:
            elem = page.wait_for_selector(selector, timeout=3000)
            if elem:
                elem.click()
                elem.fill("")  # 清空
                elem.fill(title)
                print(f"✅ 标题已填写: {title}")
                return True
        except Exception:
            continue

    print("⚠️  未找到标题输入框，请手动填写")
    return False


def fill_body(page, body_text: str):
    """填写文章正文"""
    # 头条编辑器选择器
    editor_selectors = [
        '.ProseMirror',
        '.ql-editor',
        '[contenteditable="true"]',
        '.editor-content',
        '.article-editor',
    ]

    for selector in editor_selectors:
        try:
            elem = page.wait_for_selector(selector, timeout=3000)
            if elem:
                elem.click()
                # 使用键盘快捷键全选并替换
                page.keyboard.press("Meta+a")
                time.sleep(0.3)

                # 分段输入（避免一次性粘贴过长导致编辑器卡顿）
                paragraphs = body_text.split("\n\n")
                for idx, para in enumerate(paragraphs):
                    if para.strip():
                        page.keyboard.type(para.strip(), delay=5)
                        if idx < len(paragraphs) - 1:
                            page.keyboard.press("Enter")
                            page.keyboard.press("Enter")

                print(f"✅ 正文已填写 ({len(body_text)} 字)")
                return True
        except Exception:
            continue

    print("⚠️  未找到编辑器，请手动粘贴正文")
    return False


def upload_cover(page, cover_path: str):
    """上传封面图"""
    if not cover_path:
        print("⚠️  无封面图")
        return False

    try:
        # 查找封面上传区域
        cover_selectors = [
            '.cover-upload input[type="file"]',
            '.upload-cover input[type="file"]',
            'input[type="file"][accept*="image"]',
        ]

        for selector in cover_selectors:
            try:
                elem = page.query_selector(selector)
                if elem:
                    elem.set_input_files(cover_path)
                    time.sleep(3)  # 等待上传完成
                    print(f"✅ 封面图已上传: {Path(cover_path).name}")
                    return True
            except Exception:
                continue

        print("⚠️  未找到封面上传区域，请手动上传")
        return False
    except Exception as e:
        print(f"⚠️  封面上传失败: {e}")
        return False


def add_tags(page, tags: list):
    """添加标签/话题"""
    if not tags:
        return

    tag_selectors = [
        'input[placeholder*="标签"]',
        'input[placeholder*="话题"]',
        '.tag-input input',
    ]

    for selector in tag_selectors:
        try:
            elem = page.wait_for_selector(selector, timeout=3000)
            if elem:
                for tag in tags[:5]:  # 头条最多5个标签
                    elem.click()
                    elem.fill(tag)
                    page.keyboard.press("Enter")
                    time.sleep(0.5)
                print(f"✅ 标签已添加: {', '.join(tags[:5])}")
                return
        except Exception:
            continue

    print("⚠️  未找到标签输入框，请手动添加")


def click_publish(page):
    """点击发布按钮"""
    publish_selectors = [
        'button:has-text("发布")',
        'button:has-text("Publish")',
        '.publish-btn',
        '[data-testid="publish-button"]',
    ]

    for selector in publish_selectors:
        try:
            btn = page.wait_for_selector(selector, timeout=3000)
            if btn:
                btn.click()
                time.sleep(3)
                print("✅ 已点击发布按钮")
                return True
        except Exception:
            continue

    print("⚠️  未找到发布按钮，请手动发布")
    return False


# ============================================================
# 主流程
# ============================================================

class Colors:
    OK = "\033[92m"
    WARN = "\033[93m"
    FAIL = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def main():
    if len(sys.argv) < 2:
        print("用法: python3 Scripts/publish_toutiao.py <T6终稿路径> [--publish] [--debug]")
        print()
        print("示例:")
        print("  python3 Scripts/publish_toutiao.py outputs/T6_final_头条.md         # 预览模式")
        print("  python3 Scripts/publish_toutiao.py outputs/T6_final_头条.md --publish  # 自动发布")
        sys.exit(1)

    md_path = sys.argv[1]
    do_publish = "--publish" in sys.argv
    debug_mode = "--debug" in sys.argv

    if not Path(md_path).exists():
        print(f"❌ 文件不存在: {md_path}")
        sys.exit(1)

    # Step 1: 解析文章
    print(f"\n{Colors.BOLD}━━━ ContentFleet · 头条自动发布 ━━━{Colors.RESET}\n")
    print(f"📄 解析文章: {md_path}")

    article = parse_t6_article(md_path)

    print(f"  标题: {article['title']}")
    print(f"  正文: {len(article['body'])} 字")
    print(f"  配图: {len(article['images'])} 张")
    print(f"  封面: {Path(article['cover_image']).name if article['cover_image'] else '无'}")
    print(f"  标签: {', '.join(article['tags']) if article['tags'] else '无'}")

    # Step 2: 转换正文
    body_text = md_to_toutiao_text(article["body"])

    if debug_mode:
        print(f"\n{Colors.DIM}--- 正文预览(前500字) ---{Colors.RESET}")
        print(body_text[:500])
        print(f"{Colors.DIM}--- 预览结束 ---{Colors.RESET}\n")

    # Step 3: 连接浏览器
    print(f"\n🔌 连接 Chrome...")
    pw, browser = connect_to_chrome()

    try:
        context = browser.contexts[0]
        page = context.new_page()

        # Step 4: 检查登录状态
        print("🔑 检查登录状态...")
        if not check_login_status(page):
            sys.exit(1)

        # Step 5: 填写内容
        print(f"\n📝 填写文章内容...")
        fill_title(page, article["title"])
        fill_body(page, body_text)

        # Step 6: 上传封面图
        if article["cover_image"]:
            print(f"\n🖼️  上传封面图...")
            upload_cover(page, article["cover_image"])

        # Step 7: 添加标签
        if article["tags"]:
            print(f"\n🏷️  添加标签...")
            add_tags(page, article["tags"])

        # Step 8: 发布或预览
        if do_publish:
            print(f"\n{Colors.BOLD}🚀 正在发布...{Colors.RESET}")
            if click_publish(page):
                print(f"\n{Colors.OK}✅ 文章已成功发布到头条号{Colors.RESET}")
            else:
                print(f"\n{Colors.WARN}⚠️  自动发布失败，请手动点击发布按钮{Colors.RESET}")
        else:
            print(f"\n{Colors.BOLD}🏁 预览模式 — 文章已填入编辑器{Colors.RESET}")
            print(f"   请在浏览器中检查内容，确认无误后:")
            print(f"   • 手动点击发布按钮")
            print(f"   • 或重新运行脚本并加 --publish 参数")
            if not debug_mode:
                input(f"\n   按 Enter 关闭此脚本...")

    except Exception as e:
        print(f"\n{Colors.FAIL}❌ 发生错误: {e}{Colors.RESET}")
        if debug_mode:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    finally:
        if not debug_mode:
            page.close()
            pw.stop()


if __name__ == "__main__":
    main()
