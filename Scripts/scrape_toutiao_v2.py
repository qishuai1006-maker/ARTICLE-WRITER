#!/usr/bin/env python3
"""
头条爆款采集器 v2.0
====================
分两步采集:
1. 用浏览器工具提取搜索结果（标题+文章ID）
2. 用 curl 从移动端页面提取互动数据（点赞/评论/收藏/展现）

用法:
  手动在浏览器工具中打开搜索页，复制文章列表到 articles.json
  然后: python3 scrape_toutiao_v2.py articles.json
"""
import json, sys, re, subprocess, time
from urllib.parse import unquote

def get_article_stats(article_id):
    """从头条移动端页面提取互动数据"""
    url = f"https://m.toutiao.com/i{article_id}/"
    try:
        r = subprocess.run(
            ['curl', '-s', '-L', '--max-time', '10',
             '-H', 'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
             url],
            capture_output=True, text=True, timeout=15
        )
        html = r.stdout
        
        # 提取 RENDER_DATA 中的 JSON
        m = re.search(r'<script id="RENDER_DATA" type="application/json">(.+?)</script>', html)
        if not m:
            return None
        
        raw = unquote(unquote(m.group(1)))
        data = json.loads(raw)
        
        info = data.get('articleInfo', {})
        seo = data.get('seoTDK', {})
        media = info.get('mediaUser', {})
        
        return {
            'title': info.get('title', ''),
            'author': info.get('detailSource', '') or media.get('screenName', ''),
            'publish_time': info.get('publishTime', ''),
            'digg_count': int(info.get('diggCount', 0)),
            'comment_count': int(info.get('commentCount', 0)),
            'repost_count': int(info.get('repostCount', 0)),
            'repin_count': int(info.get('repinCount', 0)),
            'impression_count': int(info.get('impressionCount', 0)),
            'follower_count': media.get('followerCount', ''),
            'article_url': f"https://www.toutiao.com/article/{article_id}/",
            'article_id': article_id,
        }
    except Exception as e:
        print(f"  ❌ 获取 {article_id} 失败: {e}", file=sys.stderr)
        return None

def main():
    if len(sys.argv) < 2:
        print("用法: python3 scrape_toutiao_v2.py <articles.json>")
        print("  articles.json 格式: [{\"title\": \"...\", \"articleId\": \"7123...\"}, ...]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    with open(input_file) as f:
        articles = json.load(f)
    
    print(f"📋 共 {len(articles)} 篇文章待处理\n")
    
    results = []
    for i, art in enumerate(articles):
        aid = art.get('articleId', '').lstrip('a')
        if not aid:
            continue
        
        print(f"[{i+1}/{len(articles)}] {art.get('title', aid)[:40]}...")
        stats = get_article_stats(aid)
        
        if stats:
            total = stats['digg_count'] + stats['comment_count'] + stats['repost_count'] + stats['repin_count']
            print(f"  👍{stats['digg_count']} 💬{stats['comment_count']} 🔄{stats['repost_count']} ⭐{stats['repin_count']} 👁{stats['impression_count']} | 总互动: {total}")
            stats['total_interaction'] = total
            results.append(stats)
        else:
            print(f"  ⚠️ 数据获取失败")
        
        time.sleep(1)  # 限速
    
    # 筛选爆款（总互动>=100）
    hot = [r for r in results if r['total_interaction'] >= 100]
    hot.sort(key=lambda x: x['total_interaction'], reverse=True)
    
    print(f"\n{'='*50}")
    print(f"📊 采集完成:")
    print(f"  总文章: {len(results)}")
    print(f"  爆款(互动≥100): {len(hot)}")
    
    # 保存
    out_file = input_file.replace('.json', '_results.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    hot_file = input_file.replace('.json', '_hot.json')
    with open(hot_file, 'w', encoding='utf-8') as f:
        json.dump(hot, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 全部结果: {out_file}")
    print(f"📁 爆款数据: {hot_file}")
    
    if hot:
        print(f"\n🔥 爆款文章:")
        for h in hot:
            print(f"  [{h['total_interaction']}] {h['title'][:50]}... ({h['author']})")

if __name__ == '__main__':
    main()
