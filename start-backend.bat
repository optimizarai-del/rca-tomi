@echo off
title RCA Backend
cd /d "%~dp0backend"
echo ============================
echo   RCA - Backend (FastAPI)
echo   http://localhost:8000
echo ============================
python run.py
pause
