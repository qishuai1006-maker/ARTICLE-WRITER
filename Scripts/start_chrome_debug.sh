#!/bin/bash
# ContentFleet · Chrome 远程调试模式启动脚本
# 用法: bash Scripts/start_chrome_debug.sh
#
# 启动 Chrome 并开启 CDP 远程调试端口(9222)
# Playwright 通过此端口连接已登录的浏览器实例
# 确保在此 Chrome 中登录 mp.toutiao.com 后，即可运行 publish_toutiao.py

PORT=9222

# 检查端口是否已被占用
if lsof -i :$PORT > /dev/null 2>&1; then
    echo "✅ Chrome 调试端口 $PORT 已在使用中"
    echo "   如需重启，请先关闭现有 Chrome 实例"
    exit 0
fi

echo "🚀 启动 Chrome (远程调试端口: $PORT)..."
echo "   请在打开的浏览器中登录 mp.toutiao.com"
echo ""

# macOS Chrome 路径
CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

if [ ! -f "$CHROME_PATH" ]; then
    echo "❌ 未找到 Chrome，请确认安装路径"
    exit 1
fi

# 启动 Chrome
# --remote-debugging-port: CDP 调试端口
# --user-data-dir: 使用独立 profile（不影响日常 Chrome 使用）
#   如果想复用已有 Chrome 配置（已登录的 cookie），去掉 --user-data-dir 参数
"$CHROME_PATH" \
    --remote-debugging-port=$PORT \
    --no-first-run \
    "https://mp.toutiao.com" &

echo ""
echo "✅ Chrome 已启动"
echo "   1. 请在浏览器中登录头条号"
echo "   2. 登录后运行: python3 Scripts/publish_toutiao.py outputs/T6_final_头条.md"
