#!/usr/bin/env bash
cd "$(dirname "$0")"

if [ ! -f "venv/bin/activate" ]; then
    echo "错误: 未检测到虚拟环境，请先运行 ./install.sh 进行安装。"
    exit 1
fi

echo "正在启动 Gradio WebUI..."
echo "默认地址: http://0.0.0.0:5600"
echo "按 Ctrl+C 可停止服务。"
echo

source venv/bin/activate
exec python src/gradio_app.py
