@echo off
chcp 65001 > nul
title ZaloTask Assistant - Trợ Lý Nhắc Việc & Gửi Zalo
cd /d "%~dp0"

echo =====================================================================
echo    ĐANG KHỞI ĐỘNG ZALOTASK ASSISTANT (WEB DASHBOARD & SCHEDULER)
echo =====================================================================
echo.

python run.py

pause
