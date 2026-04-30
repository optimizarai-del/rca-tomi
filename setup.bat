@echo off
title RCA Setup
cd /d "%~dp0"
echo ===========================================
echo   RCA - Setup inicial (correr 1 vez)
echo ===========================================
echo.

REM ─── Verificar Python ───
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python no esta instalado o no esta en PATH.
    echo Descargalo de https://www.python.org/downloads/ ^(3.11+^)
    pause
    exit /b 1
)

REM ─── Verificar Node ───
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js no esta instalado o no esta en PATH.
    echo Descargalo de https://nodejs.org/ ^(20+^)
    pause
    exit /b 1
)

echo [1/4] Backend: creando venv y instalando deps...
cd backend
if not exist ".venv" (
    python -m venv .venv
    if errorlevel 1 ( echo [ERROR] No se pudo crear venv & pause & exit /b 1 )
)
call .venv\Scripts\python.exe -m pip install --quiet --upgrade pip
call .venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 ( echo [ERROR] pip install fallo & pause & exit /b 1 )

echo.
echo [2/4] Backend: configurando .env...
if not exist ".env" (
    copy /Y .env.example .env >nul
    echo       .env creado. Editalo y pega tu ANTHROPIC_API_KEY.
) else (
    echo       .env ya existe, no se toca.
)

echo.
echo [3/4] Backend: cargando datos demo...
call .venv\Scripts\python.exe -m app.seed
cd ..

echo.
echo [4/4] Frontend: instalando deps...
cd frontend
if not exist ".env" (
    echo VITE_API_URL=http://localhost:8010> .env
    echo       .env creado apuntando al backend :8010
)
call npm install
if errorlevel 1 ( echo [ERROR] npm install fallo & cd .. & pause & exit /b 1 )
cd ..

echo.
echo ===========================================
echo   Setup completo!
echo ===========================================
echo.
echo Proximos pasos:
echo   1. Editar backend\.env y pegar tu ANTHROPIC_API_KEY
echo      ^(conseguila en https://console.anthropic.com^)
echo   2. Doble-click en start-backend.bat
echo   3. Doble-click en start-frontend.bat
echo   4. Abrir http://localhost:5175
echo   5. Login: admin@demo.com / demo1234
echo.
pause
