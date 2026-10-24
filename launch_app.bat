@echo off
title Launch Police AI Platform
cd /d "%~dp0"
echo ============================================================
echo   LAUNCHING POLICE BIOMETRIC IDENTIFICATION PLATFORM
echo ============================================================
echo.
echo Opening Web Command Center in your default browser...
start http://localhost:8000
echo.
echo If the backend server is not running, run: start_backend.bat
echo Web App URL: http://localhost:8000
echo Mobile on same Wi-Fi: http://192.168.1.8:8000
echo.
pause
