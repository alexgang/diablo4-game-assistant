@echo off
chcp 65001 >nul 2>&1
title 暗黑破坏神4 游戏助手
cd /d "%~dp0"

echo ════════════════════════════════════════════════
echo            暗黑破坏神4 游戏助手 一键启动
echo ════════════════════════════════════════════════
echo.
echo 正在启动,请稍候...
echo   - 自动检测并启动 SDK 服务器(如未运行)
echo   - 自动启动游戏助手主程序
echo   - 窗口可直接点击顶部 header 拖动
echo.
echo 关闭本窗口不会关闭游戏助手,如需退出请关闭主程序窗口。
echo ════════════════════════════════════════════════
echo.

REM 优先使用项目内 Python,其次用系统 Python
if exist "pylibs\python.exe" (
    set "PYTHON=pylibs\python.exe"
) else if exist "venv\Scripts\python.exe" (
    set "PYTHON=venv\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

REM 启动主程序(会自动拉起 SDK 服务器)
"%PYTHON%" main.py

REM 如果主程序异常退出,暂停以便查看错误
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ════════════════════════════════════════════════
    echo 程序异常退出(错误码: %ERRORLEVEL%)
    echo ════════════════════════════════════════════════
    pause
)
