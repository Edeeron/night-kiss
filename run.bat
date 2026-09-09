@echo off
chcp 65001 >nul 2>&1
title Night-Night Kiss (晚安吻)
echo.
echo   ╔═══════════════════════════════════════════╗
echo   ║                                           ║
echo   ║     Night-Night Kiss  晚安吻              ║
echo   ║     用 AI 的声音，陪你读每一本书           ║
echo   ║                                           ║
echo   ╚═══════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: ── 检查 Python ──
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [错误] 未检测到 Python，请先安装 Python 3.10+
    echo  下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: ── 安装依赖 ──
echo  正在检查依赖...
pip install flask requests -q 2>nul

:: ── 创建数据目录 ──
if not exist "data\voice" mkdir "data\voice"
if not exist "data\books" mkdir "data\books"

:: ── 启动服务 ──
echo.
echo  正在启动晚安吻...
echo  启动后请在浏览器打开下方地址 ↓
echo.
python app\server.py

pause
