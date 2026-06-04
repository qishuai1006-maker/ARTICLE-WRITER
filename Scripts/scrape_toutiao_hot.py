#!/usr/bin/env python3
"""
头条爆款采集器 v1.0 (scrape_toutiao_hot.py)
============================================
采集今日头条上家电赛道的爆款文章（互动过百），
存入本地 JSONL 文件，可批量导入飞书多维表格。

前置条件:
  1. Chrome 以远程调试模式启动:
     /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
  2. Chrome 中已登录 toutiao.com（有搜索权限）
  3. pip install playwright

用法:
  python3 Scripts/scrape_toutiao_hot.py [--max-pages 3] [--delay 5] [--output outputs/hot_articles.jsonl]
"""

import re
import sys
import time
import json
import random
import argparse
from pathlib import Path
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ 需要安装 Playwright: pip install playwright && playwright install chromium")
    sys.exit(1)


# ============================================================
# 配置
# ============================================================

# 搜索关键词（5个品类）
SEARCH_QUERIES = {
    "电视": ["电视推荐", "电视选购", "电视品牌", "智能电视推荐"],
    "冰箱": ["冰箱推荐", "冰箱选购", "冰箱品牌", "冰箱性价比"],
    "洗衣机": ["洗衣机推荐", "洗衣机选购", "洗衣机品牌", "滚筒洗衣机推荐"],
    "油烟机": ["油烟机推荐", "油烟机选购", "油烟机品牌", "抽油烟机推荐"],
    "空调": ["空调推荐", "空调选购", "空调品牌", "空调性价比"],
}

# 互动阈值
INTERACTION_THRESHOLD = 100

# 默认延迟（秒）- 每次操作之间
DEFAULT_DELAY = 5

# Chrome CDP 端口
CDP_PORT = 9222


# ============================================================
# 浏览器连接
# ============================================================

def launch_browser(p):
    """启动 Playwright 管理的新 Chromium 实例（不需要外部 Chrome）"""
    import os
    # 查找已安装的 Chromium
    base = os.path.expanduser("~/Library/Caches/ms-playwright")
    for ver in ["chromium-1223", "chromium-1217", "chromium-1208"]:
        for arch in ["chrome-mac-arm64", "chrome-mac"]:
            exe = os.path.join(base, ver, arch, "Google Chrome for Testing.app", "Contents", "MacOS", "Google Chrome for Testing")
            if os.path.exists(exe):
                break
        else:
            continue
        break
    else:
        exe = None  # 未找到，使用默认
    
    try:
        browser = p.chromium.launch(
            headless=False,  # 有显示器，用非无头模式
            executable_path=exe,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            ]
        )
        print(f"✅ Chromium 已启动")
        return browser
    except Exception as e:
        print(f"❌ 浏览器启动失败: {e}")
        print(f"   请运行: playwright install chromium")
        sys.exit(1)


# ============================================================
# 数据提取
# ============================================================

def parse_interaction_count(text: str) -> int:
    """解析互动数量（'1.2万' → 12000, '567' → 567, '3.5万' → 35000）"""
    if not text:
        return 0
    text = text.strip()
    # 去除非数字字符
    match = re.search(r'([\d.]+)\s*(万|w)?', text)
    if not match:
        return 0
    num = float(match.group(1))
    unit = match.group(2)
    if unit in ('万', 'w'):
        num *= 10000
    return int(num)


def extract_articles_from_search(page) -> list:
    """从搜索结果页面提取文章列表"""
    articles = []
    
    try:
        # 等待搜索结果加载
        page.wait_for_selector('[class*="result-content"], [class*="cs-pc-card"], a[href*="toutiao.com"]', timeout=10000)
        time.sleep(2)
    except Exception as e:
        print(f"  ⚠️ 搜索结果加载超时: {e}")
        return articles
    
    # 通过 JS 提取所有搜索结果中的文章链接和标题
    raw_articles = page.evaluate("""
    () => {
        const results = [];
        // 搜索结果卡片
        const cards = document.querySelectorAll('a[href*="toutiao.com/article"], a[href*="toutiao.com/group"], a[href*="www.toutiao.com/a"]');
        cards.forEach(card => {
            const href = card.href;
            const title = card.textContent?.trim() || '';
            if (title && href && !href.includes('search')) {
                results.push({ title, href });
            }
        });
        // 也尝试从更通用的结构提取
        const links = document.querySelectorAll('a[href*="/article/"], a[href*="/group/"]');
        links.forEach(link => {
            const href = link.href;
            const title = link.textContent?.trim() || '';
            if (title.length > 5 && href && !results.some(r => r.href === href)) {
                results.push({ title, href });
            }
        });
        return results;
    }
    """)
    
    # 提取评论数（搜索结果页通常会显示）
    comment_counts = page.evaluate("""
    () => {
        const counts = {};
        // 查找所有评论数标记
        const commentEls = document.querySelectorAll('[class*="comment"], a[href*="comment"]');
        const allText = document.querySelectorAll('span, a, div');
        allText.forEach(el => {
            const text = el.textContent?.trim() || '';
            const match = text.match(/(\\d+)\\s*评论/);
            if (match) {
                counts[el.closest('a, [class*="card"]')?.querySelector('a')?.href || ''] = parseInt(match[1]);
            }
        });
        return counts;
    }
    """)
    
    for raw in raw_articles:
        title = raw.get('title', '').strip()
        href = raw.get('href', '')
        if not title or len(title) < 5:
            continue
        # 过滤掉搜索结果中的标签链接
        if any(skip in title for skip in ['搜索', '查看更多', '头条热榜', '去抖音']):
            continue
        articles.append({
            'title': title[:200],  # 截断过长标题
            'url': href,
            'comments_from_search': comment_counts.get(href, 0),
        })
    
    return articles


def get_article_details(page, url: str) -> dict:
    """进入文章详情页获取互动数据"""
    details = {'likes': 0, 'comments': 0, 'favorites': 0}
    
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=15000)
        time.sleep(2)
        
        # 提取互动数据
        interactions = page.evaluate("""
        () => {
            const result = { likes: 0, comments: 0, favorites: 0 };
            const allText = document.body.innerText;
            
            // 尝试从页面提取点赞数
            const likePatterns = [
                /赞\\s*(\\d+)/,
                /(\\d+)\\s*赞/,
                /(\\d+)\\s*点赞/,
                /digg_count["']?\\s*[:>]\\s*(\\d+)/,
            ];
            for (const p of likePatterns) {
                const m = allText.match(p);
                if (m) { result.likes = parseInt(m[1]); break; }
            }
            
            // 评论数
            const commentPatterns = [
                /评论\\s*(\\d+)/,
                /(\\d+)\\s*评论/,
                /comment_count["']?\\s*[:>]\\s*(\\d+)/,
            ];
            for (const p of commentPatterns) {
                const m = allText.match(p);
                if (m) { result.comments = parseInt(m[1]); break; }
            }
            
            // 收藏数
            const favPatterns = [
                /收藏\\s*(\\d+)/,
                /(\\d+)\\s*收藏/,
                /collect_count["']?\\s*[:>]\\s*(\\d+)/,
            ];
            for (const p of favPatterns) {
                const m = allText.match(p);
                if (m) { result.favorites = parseInt(m[1]); break; }
            }
            
            // 尝试从 JSON-LD 或 script 标签中提取
            const scripts = document.querySelectorAll('script[type="application/ld+json"], script');
            for (const s of scripts) {
                const text = s.textContent || '';
                try {
                    // 查找 SSR 数据
                    if (text.includes('digg_count') || text.includes('comment_count')) {
                        const data = JSON.parse(text);
                        if (data.digg_count) result.likes = data.digg_count;
                        if (data.comment_count) result.comments = data.comment_count;
                        if (data.collect_count) result.favorites = data.collect_count;
                    }
                } catch(e) {}
            }
            
            // 从 meta 标签提取
            const metaEls = document.querySelectorAll('meta[name*="comment"], meta[property*="comment"]');
            metaEls.forEach(m => {
                const content = m.getAttribute('content') || '';
                const num = parseInt(content);
                if (num) result.comments = num;
            });
            
            return result;
        }
        """)
        
        details.update(interactions)
        
        # 提取作者信息
        author = page.evaluate("""
        () => {
            // 尝试多种方式获取作者名
            const selectors = [
                '[class*="author-name"]',
                '[class*="user-name"]',
                '[class*="source"]',
                'a[href*="user/"]',
                '.media-name',
            ];
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el && el.textContent?.trim()) return el.textContent.trim();
            }
            return '';
        }
        """)
        details['author'] = author
        
        # 提取发布日期
        pub_date = page.evaluate("""
        () => {
            const selectors = [
                '[class*="publish-time"]',
                '[class*="article-time"]',
                'time',
                '[class*="date"]',
            ];
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el) {
                    const text = el.textContent?.trim() || el.getAttribute('datetime') || '';
                    if (text) return text;
                }
            }
            return '';
        }
        """)
        details['publish_date'] = pub_date
        
    except Exception as e:
        print(f"    ⚠️ 获取详情失败: {e}")
    
    return details


# ============================================================
# 搜索采集
# ============================================================

def search_and_collect(page, category: str, query: str, max_pages: int = 3, delay: float = DEFAULT_DELAY) -> list:
    """执行一次搜索并采集文章"""
    collected = []
    
    for page_num in range(max_pages):
        url = f"https://so.toutiao.com/search?keyword={query}&pd=information&dvpf=pc&page_num={page_num}"
        print(f"\n  📄 搜索: [{category}] {query} (第{page_num+1}页)")
        
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=15000)
        except Exception as e:
            print(f"    ⚠️ 页面加载失败: {e}")
            continue
        
        # 检查是否有验证码
        has_captcha = page.evaluate("""
        () => {
            return !!document.querySelector('[class*="captcha"], [class*="verify"], iframe[src*="captcha"]');
        }
        """)
        
        if has_captcha:
            print(f"    🚫 触发验证码！请手动完成验证...")
            print(f"    等待 60 秒，请在浏览器中完成验证...")
            time.sleep(60)
            # 验证后重试
            try:
                page.reload(wait_until='domcontentloaded', timeout=15000)
            except:
                continue
        
        time.sleep(delay + random.uniform(0, 2))
        
        # 提取文章列表
        articles = extract_articles_from_search(page)
        print(f"    找到 {len(articles)} 篇文章")
        
        # 逐篇获取详情（互动数据）
        for i, article in enumerate(articles):
            print(f"    [{i+1}/{len(articles)}] {article['title'][:40]}...", end="")
            
            details = get_article_details(page, article['url'])
            
            likes = details.get('likes', 0)
            comments = details.get('comments', 0) or article.get('comments_from_search', 0)
            favorites = details.get('favorites', 0)
            total = likes + comments + favorites
            
            article.update({
                'category': category,
                'author': details.get('author', ''),
                'likes': likes,
                'comments': comments,
                'favorites': favorites,
                'total_interaction': total,
                'publish_date': details.get('publish_date', ''),
                'collected_at': datetime.now().isoformat(),
            })
            
            if total >= INTERACTION_THRESHOLD:
                print(f" ✅ 总互动={total}")
                collected.append(article)
            else:
                print(f" ⏭️ 总互动={total} (< {INTERACTION_THRESHOLD})")
            
            # 随机延迟避免反爬
            time.sleep(delay + random.uniform(1, 3))
        
        # 翻页延迟
        time.sleep(delay + random.uniform(2, 5))
    
    return collected


# ============================================================
# 存储
# ============================================================

def save_to_jsonl(articles: list, output_path: str):
    """追加写入 JSONL 文件"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'a', encoding='utf-8') as f:
        for article in articles:
            f.write(json.dumps(article, ensure_ascii=False) + '\n')
    
    print(f"\n💾 已保存 {len(articles)} 条到 {path}")


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='头条爆款采集器 v1.0')
    parser.add_argument('--max-pages', type=int, default=3, help='每个搜索词的最大页数')
    parser.add_argument('--delay', type=float, default=DEFAULT_DELAY, help='请求间隔（秒）')
    parser.add_argument('--output', type=str, default='outputs/hot_articles.jsonl', help='输出文件路径')
    parser.add_argument('--categories', type=str, nargs='*', default=None, help='限定品类（电视/冰箱/洗衣机/油烟机/空调）')
    parser.add_argument('--test', action='store_true', help='测试模式：只采集1个品类1个搜索词1页')
    args = parser.parse_args()
    
    print("━" * 50)
    print("  头条爆款采集器 v1.0")
    print("━" * 50)
    
    # 确定采集范围
    categories = args.categories or list(SEARCH_QUERIES.keys())
    if args.test:
        categories = categories[:1]
    
    print(f"\n📋 采集配置:")
    print(f"  品类: {', '.join(categories)}")
    print(f"  每词最大页数: {args.max_pages}")
    print(f"  请求间隔: {args.delay}s")
    print(f"  互动阈值: {INTERACTION_THRESHOLD}")
    print(f"  输出: {args.output}")
    if args.test:
        print(f"  ⚡ 测试模式（仅1个品类1个搜索词）")
    
    # 启动浏览器
    print(f"\n🚀 启动浏览器...")
    pw = sync_playwright().start()
    browser = launch_browser(pw)
    
    try:
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        total_collected = []
        
        for category in categories:
            queries = SEARCH_QUERIES.get(category, [])
            if args.test:
                queries = queries[:1]
            
            print(f"\n{'='*50}")
            print(f"🏷️ 品类: {category}")
            print(f"{'='*50}")
            
            for query in queries:
                articles = search_and_collect(
                    page, category, query,
                    max_pages=1 if args.test else args.max_pages,
                    delay=args.delay,
                )
                total_collected.extend(articles)
                
                # 每批保存一次
                if articles:
                    save_to_jsonl(articles, args.output)
        
        # 汇总
        print(f"\n{'='*50}")
        print(f"📊 采集完成")
        print(f"  总爆款文章: {len(total_collected)}")
        
        if total_collected:
            by_category = {}
            for a in total_collected:
                cat = a.get('category', '未知')
                by_category[cat] = by_category.get(cat, 0) + 1
            print(f"  分品类:")
            for cat, count in by_category.items():
                print(f"    {cat}: {count} 篇")
        
        print(f"\n📁 数据已保存到: {args.output}")
        print(f"   可用以下命令导入飞书多维表格:")
        print(f"   python3 Scripts/import_hot_to_feishu.py {args.output}")
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️ 用户中断，已保存的数据不丢失")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        page.close()
        pw.stop()


if __name__ == "__main__":
    main()
