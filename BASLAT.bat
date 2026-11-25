@echo off
chcp 65001 >nul
title GUNS.LOL MEGA-TURBO VIEW BOT - 16GB PC EDITION
color 0b
echo ===============================================================
echo            GUNS.LOL MEGA-TURBO VIEW BOT (16GB RAM)
echo ===============================================================
echo  Hedef: https://guns.lol/osintowner
echo  Worker: 12 Thread Eşzamanlı Browser
echo  Dashboard: http://127.0.0.1:10000
echo ===============================================================
echo.

cd /d "%~dp0"

echo [1/2] Web Dashboard tarayicida aciliyor...
start http://127.0.0.1:10000

echo [2/2] Turbo Bot motoru baslatiliyor...
echo.
python guns_viewbot.py -u https://guns.lol/osintowner -t 12 --timeout 20

pause
