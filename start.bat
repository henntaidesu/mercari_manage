@echo off
chcp 65001 >nul
echo ========================================
echo   mercari 物品管理 启动脚本
echo ========================================
echo.

set ROOT=%~dp0
set BACKEND=%ROOT%backend
set WEBSIDE=%ROOT%webside

echo [1/2] 激活 conda 环境 mercari 并启动后端...
call conda activate mercari

cd /d %BACKEND%
start /b python -m uvicorn main:app --host 0.0.0.0 --port 8000

timeout /t 2 /nobreak >nul

echo [2/2] 启动前端...
cd /d %WEBSIDE%

echo.
echo ========================================
echo   前端地址: http://localhost:9600
echo   后端API:  http://localhost:8000
echo   API文档:  http://localhost:8000/docs
echo   按 Ctrl+C 停止所有服务
echo ========================================
echo.

npm run dev
