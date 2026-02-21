@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo 错误: 未检测到虚拟环境，请先运行 install.bat 进行安装。
    pause
    exit /b 1
)

echo 正在启动 Gradio WebUI...
echo 默认地址: http://0.0.0.0:5600
echo 按 Ctrl+C 可停止服务。
echo.

call venv\Scripts\activate.bat
python src/gradio_app.py

pause
