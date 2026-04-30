@echo off
title RCA Frontend
cd /d "%~dp0frontend"
echo ============================
echo   RCA - Frontend (Vite)
echo   http://localhost:5175
echo ============================

if not exist "node_modules" (
    echo [setup] No hay node_modules. Corre setup.bat una vez antes.
    pause
    exit /b 1
)

if not exist ".env" (
    echo VITE_API_URL=http://localhost:8010> .env
    echo [setup] .env creado apuntando al backend en :8010
)

call npm run dev -- --port 5175 --strictPort
pause
