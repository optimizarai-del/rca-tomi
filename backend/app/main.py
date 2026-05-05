import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routers import (
    auth, users, obras, cuadrillas, materiales, proveedores,
    ordenes, eventos, dashboard, whatsapp, agent,
    clientes, regimenes_fiscales, etapas, movimientos, aportes, comprobantes,
)

load_dotenv(override=True)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="RCA. — Sistema de Gestión de Obras", version="0.4.0")

origins = os.getenv("CORS_ORIGINS", "http://localhost:5175,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROUTERS = [
    auth, users,
    regimenes_fiscales, clientes,
    obras, etapas,
    movimientos, aportes, comprobantes,
    cuadrillas, materiales, proveedores, ordenes, eventos,
    dashboard, whatsapp, agent,
]

for r in ROUTERS:
    app.include_router(r.router)


@app.get("/health")
def health():
    return {"status": "ok", "brand": "RCA.", "version": "0.4.0"}
