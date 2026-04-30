@echo off
title RCA Backend
cd /d "%~dp0backend"
echo ============================
echo   RCA - Backend (FastAPI)
echo   http://localhost:8010
echo ============================

if not exist ".venv\Scripts\python.exe" (
    echo [setup] No hay venv. Corre setup.bat una vez antes.
    pause
    exit /b 1
)

if not exist ".env" (
    if exist ".env.example" (
        echo [setup] Creando .env desde .env.example...
        copy /Y .env.example .env >nul
        echo [setup] Editá backend\.env y completá ANTHROPIC_API_KEY antes de usar el agente.
    )
)

.venv\Scripts\python.exe run.py
pause
