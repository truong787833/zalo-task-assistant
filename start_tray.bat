@echo off
chcp 65001 > nul
title ZaloTask Assistant (Khay Hệ Thống)
cd /d "%~dp0"

echo =====================================================================
echo    KHỞI CHẠY ZALOTASK ASSISTANT VỚI KHAY HỆ THỐNG (SYSTEM TRAY)
echo =====================================================================
echo [*] Đang khởi động và thu nhỏ vào góc phải màn hình...
echo [*] Bạn có thể bấm đúp vào biểu tượng quả chuông ở khay hệ thống để mở Web.
echo.

python tray.py
