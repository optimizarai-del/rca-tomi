#!/usr/bin/env bash
# RCA - Setup inicial (Mac / Linux). Correr 1 vez tras clonar el repo.
set -e

cd "$(dirname "$0")"

echo "==========================================="
echo "  RCA - Setup inicial"
echo "==========================================="

command -v python3 >/dev/null 2>&1 || { echo "[ERROR] Python 3.11+ no instalado"; exit 1; }
command -v node    >/dev/null 2>&1 || { echo "[ERROR] Node 20+ no instalado"; exit 1; }
command -v npm     >/dev/null 2>&1 || { echo "[ERROR] npm no instalado"; exit 1; }

echo
echo "[1/4] Backend: creando venv e instalando deps..."
cd backend
if [ ! -d ".venv" ]; then python3 -m venv .venv 2>/dev/null || python -m venv .venv; fi
# Detectar layout Unix vs Windows (Git Bash)
if [ -f ".venv/bin/python" ]; then
    PY=".venv/bin/python"
elif [ -f ".venv/Scripts/python.exe" ]; then
    PY=".venv/Scripts/python.exe"
else
    echo "[ERROR] No se encontro python en .venv"; exit 1
fi
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install -r requirements.txt

echo
echo "[2/4] Backend: configurando .env..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "      .env creado. Editalo y pega tu ANTHROPIC_API_KEY."
else
    echo "      .env ya existe, no se toca."
fi

echo
echo "[3/4] Backend: cargando datos demo..."
"$PY" -m app.seed
cd ..

echo
echo "[4/4] Frontend: instalando deps..."
cd frontend
if [ ! -f ".env" ]; then
    echo "VITE_API_URL=http://localhost:8010" > .env
    echo "      .env creado apuntando al backend :8010"
fi
npm install
cd ..

echo
echo "==========================================="
echo "  Setup completo!"
echo "==========================================="
echo
echo "Proximos pasos:"
echo "  1. Editar backend/.env y pegar tu ANTHROPIC_API_KEY"
echo "     (conseguila en https://console.anthropic.com)"
echo "  2. Terminal 1:  cd backend && .venv/bin/python run.py"
echo "  3. Terminal 2:  cd frontend && npm run dev -- --port 5175 --strictPort"
echo "  4. Abrir http://localhost:5175"
echo "  5. Login: admin@demo.com / demo1234"
