@echo off
title RCA Frontend
cd /d "%~dp0frontend"
echo ============================
echo   RCA - Frontend (Vite)
echo   http://localhost:5173
echo ============================
call npm run dev
pause
