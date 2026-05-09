import json
import subprocess
import argparse
import sys
import re
import os

def fetch_youtube_data(query, is_search=False, limit=20, recent_months=6):
    """
    使用系统安装的 yt-dlp 抓取 YouTube 数据
    默认应用近 6 个月时间过滤，保证资讯时效性
    """
    command = ['yt-dlp', '--dump-json', '--skip-download', '--cookies-from-browser', 'chrome']
    
    if is_search:
        # 为了应对过滤衰减，内部搜取量设为需求量的 3 倍以供沉淀
        search_limit = limit * 3 
        command.append(f"ytsearch{search_limit}:{query}")
        if recent_months > 0:
            command.extend(['--dateafter', f'today-{recent_months}months'])
    else:
        command.append(query)
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        videos = []
        
        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    data = json.loads(line)
                    videos.append({
                        "title": data.get("title"),
                        "id": data.get("id"),
                        "url": data.get("webpage_url") or f"https://www.youtube.com/watch?v={data.get('id')}",
                        "view_count": data.get("view_count"),
                        "uploader": data.get("uploader"),
                        "upload_date": data.get("upload_date"),
                        "duration": data.get("duration"),
                        "description": data.get("description", "")[:200] + "..." if data.get("description") else ""
                    })
                except json.JSONDecodeError:
                    continue
                    
        # 仅返回所需的前 N 个结果
        return json.dumps(videos[:limit], ensure_ascii=False, indent=2)
        
    except subprocess.CalledProcessError as e:
        return json.dumps({
            "error": "yt-dlp execution failed (bot detection or network error)", 
            "details": e.stderr.strip()
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

def fetch_subtitles(video_url, output_dir="outputs"):
    """
    抓取视频字幕（中英双语优先）并转化为带时间戳的纯文本
    """
    base_dir = "/Users/ltn/Downloads/ARTICLE WRITER"
    full_out_dir = os.path.join(base_dir, output_dir)
    if not os.path.exists(full_out_dir):
        os.makedirs(full_out_dir, exist_ok=True)
        
    command = [
        'yt-dlp', 
        '--write-auto-sub', '--write-sub',
        '--sub-lang', 'zh-Hans,zh-Hant,en', 
        '--convert-subs', 'srt', 
        '--skip-download',
        '--cookies-from-browser', 'chrome',
        '-o', f"{full_out_dir}/%(title)s.%(ext)s",
        video_url
    ]
    
    try:
        subprocess.run(command, capture_output=True, text=True, check=True)
        
        srt_files = [os.path.join(full_out_dir, f) for f in os.listdir(full_out_dir) if f.endswith('.srt')]
        if not srt_files:
            return json.dumps({"error": "No subtitles found or downloaded."}, ensure_ascii=False)
        
        latest_srt = max(srt_files, key=os.path.getmtime)
        
        with open(latest_srt, 'r', encoding='utf-8') as f:
            srt_content = f.read()
            
        txt_content = re.sub(r'^\d+\s*\n', '', srt_content, flags=re.MULTILINE)
        txt_content = re.sub(r'\n{3,}', '\n\n', txt_content).strip()
        
        txt_path = latest_srt.replace('.srt', '.txt')
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(txt_content)
            
        return json.dumps({
            "status": "SUCCESS",
            "message": "字幕生成已保存至项目 outputs 目录",
            "txt_path": txt_path,
            "preview_text": txt_content[:800] + "......"
        }, ensure_ascii=False, indent=2)
        
    except subprocess.CalledProcessError as e:
        return json.dumps({
            "error": "yt-dlp chunk failed", 
            "details": e.stderr.strip()
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="YouTube URL or search term")
    parser.add_argument("--search", action="store_true", help="Search mode")
    parser.add_argument("--limit", type=int, default=20, help="Return results limit")
    parser.add_argument("--recent-months", type=int, default=6, help="Filter by last N months (default 6; 0 to disable)")
    parser.add_argument("--subtitles", action="store_true", help="Extract subtitle TXT")
    
    args = parser.parse_args()
    
    if args.subtitles:
        print(fetch_subtitles(args.query))
    else:
        print(fetch_youtube_data(args.query, args.search, args.limit, args.recent_months))
