@echo off
title Police Biometric Dispatch - FastAPI Central Server
cd /d "%~dp0"
echo ============================================================
echo   POLICE BIOMETRIC DISPATCH - CENTRAL BACKEND SERVER
echo ============================================================
echo   LAN Endpoint: http://192.168.1.8:8000
echo   API Docs:     http://localhost:8000/docs
echo   Web Console:  http://localhost:8000/
echo ============================================================
echo.
python run.py
pause
