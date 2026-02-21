@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ========================================
echo   data_analysis_webui - Windows 安装
echo ========================================
echo.

if not exist "venv" (
    echo [1/2] 创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo 错误: 创建虚拟环境失败，请确保已安装 Python 并加入 PATH。
        exit /b 1
    )
    echo 虚拟环境已创建。
) else (
    echo [1/2] 虚拟环境已存在，跳过创建。
)

echo.
echo [2/2] 安装依赖...
call venv\Scripts\activate.bat
pip install -r requirements.txt
if errorlevel 1 (
    echo 错误: 安装依赖失败。
    exit /b 1
)

echo.
echo ========================================
echo   安装完成。使用 start.bat 启动应用。
echo ========================================
exit /b 0
