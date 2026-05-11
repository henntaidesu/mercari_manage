@echo off
chcp 65001 >nul
echo ========================================
echo   mercari 订单管理 启动脚本
echo ========================================
echo.

set ROOT=%~dp0
set BACKEND=%ROOT%backend
set WEBSIDE=%ROOT%webside

REM 默认前端为 HTTPS + 自签名证书（无 CA，浏览器提示「不安全」时点「高级」继续即可）。
REM 需要纯 HTTP、不要证书提示时，在本行前加: set MERCARI_DEV_HTTP=1
if not defined MERCARI_DEV_HTTP set MERCARI_DEV_HTTP=0

echo [1/2] 激活 conda 环境 mercari 并启动后端...
call conda activate mercari

cd /d %BACKEND%
start /b python -m uvicorn main:app --host 0.0.0.0 --port 9601

timeout /t 2 /nobreak >nul

echo [2/2] 初始化前端依赖并启动...
where node >nul 2>&1
if errorlevel 1 (
  echo [错误] 未找到 Node.js，请先安装并加入 PATH: https://nodejs.org/
  pause
  exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
  echo [错误] 未找到 npm，请检查 Node.js 安装是否完整
  pause
  exit /b 1
)

cd /d %WEBSIDE%
call npm install
if errorlevel 1 (
  echo [错误] npm install 失败，请检查网络与 package.json
  pause
  exit /b 1
)

echo.
echo ========================================
if "%MERCARI_DEV_HTTP%"=="1" (
  echo   前端 ^(HTTP^):  http://localhost:9600
  echo   局域网可用:     http://本机IP或域名:9600  ^(摄像头在非 localhost 上可能仍受限^)
) else (
  echo   前端 ^(HTTPS 自签名^): https://localhost:9600
  echo   证书: 无公信 CA，浏览器会警告 — 选「高级」→「继续访问」即可
  echo   局域网: https://本机IP或域名:9600  ^(同样点继续访问^)
)
echo   后端 API:  http://localhost:9601  ^(或本机 IP:9601^)
echo   API 文档:  http://localhost:9601/docs
echo   按 Ctrl+C 停止
echo ========================================
echo.

npm run dev
