#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "========================================"
echo "  data_analysis_webui - Linux 安装"
echo "========================================"
echo

if [ ! -d "venv" ]; then
    echo "[1/2] 创建虚拟环境..."
    python3 -m venv venv
    echo "虚拟环境已创建。"
else
    echo "[1/2] 虚拟环境已存在，跳过创建。"
fi

echo
echo "[2/2] 安装依赖..."
source venv/bin/activate
pip install -r requirements.txt

echo
echo "========================================"
echo "  安装完成。使用 ./start.sh 启动应用。"
echo "========================================"
