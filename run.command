#!/bin/bash
cd "$(dirname "$0")"

echo ""
echo "  ╔═══════════════════════════════════════════╗"
echo "  ║                                           ║"
echo "  ║     Night-Night Kiss  晚安吻              ║"
echo "  ║     用 AI 的声音，陪你读每一本书           ║"
echo "  ║                                           ║"
echo "  ╚═══════════════════════════════════════════╝"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "  [错误] 未检测到 Python3，请先安装"
    echo "  下载地址: https://www.python.org/downloads/"
    exit 1
fi

# 安装依赖
echo "  正在检查依赖..."
pip3 install -r requirements.txt -q 2>/dev/null

# 创建数据目录
mkdir -p data/voice data/books

# 启动服务
echo ""
echo "  正在启动晚安吻..."
echo "  启动后请在浏览器打开: http://localhost:5200"
echo ""
python3 app/server.py
