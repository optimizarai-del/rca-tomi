"""Servicio Sprint 24 — generación de plan de obra asistida por Claude.

Recibe contexto del usuario + datos de la obra y devuelve una estructura
con etapas, frentes y materiales sugeridos. NO crea registros — eso es
responsabilidad del endpoint de "aplicar".

Si no hay ANTHROPIC_API_KEY configurada, genera un plan placeholder
determinístico para que el sprint sea testeable sin API externa.
"""
from __future__ import annotations
import json
import logging
import os
from datetime import date, timedelta
from typing import Optional
from app import models

logger = logging.getLogger(__name__)

# Esquema esperado en resultado_json:
# {
#   "etapas": [
#     {"nombre": "...", "nro_etapa": 1, "monto_contractual": 0,
#      "porcentaje_avance": 0, "fecha_estimada": "YYYY-MM-DD",
#      "notas": "..."}
#   ],
#   "frentes": [
#     {"nombre": "...", "tipo": "estructura|mamposteria|...", "notas": "..."}
#   ],
#   "materiales_sugeridos": [
#     {"nombre": "...", "categoria": "...", "unidad": "...", "cantidad": 0, "etapa": "..."}
#   ],
#   "notas_generales": "..."
# }

SYSTEM_PROMPT = """Sos un planificador de obras de construcción experto.
El usuario te describe una obra y vos devolvés un plan estructurado JSON con:

1. ETAPAS: secuencia ordenada de etapas de la obra. Cada una con:
   - nombre: ej "Anticipo", "Etapa 1 - Cimientos y estructura"
   - nro_etapa: 0 para anticipo, 1, 2, ... para sucesivas
   - monto_contractual: estimación basada en el monto total mencionado (puede ser 0 si no se sabe)
   - porcentaje_avance: % del total de obra que representa
   - fecha_estimada: ISO date estimada de cobro/fin
   - notas: 1-2 frases con detalles claves

2. FRENTES: sub-mapas operativos (cimientos, mampostería, instalaciones, terminaciones, etc.):
   - nombre, tipo, notas

3. MATERIALES_SUGERIDOS: lista corta de los materiales clave que van a hacer falta:
   - nombre, categoria (cemento, hierro, ladrillo, áridos, instalaciones, terminaciones, herramientas)
   - unidad (bolsa, kg, m3, u, m)
   - cantidad: estimación; si no hay base usar 0 y aclarar en notas
   - etapa: nombre de la etapa donde se usa principalmente

4. NOTAS_GENERALES: 2-3 frases con riesgos, dependencias o cosas a confirmar.

REGLAS:
- Devolvé SOLO el JSON, sin texto extra ni markdown.
- Si el usuario da pocos datos, igual proponé etapas mínimas: Anticipo, Estructura, Terminaciones, Final.
- Los porcentajes_avance de las etapas tienen que sumar ~100.
- Las fechas estimadas son secuenciales: la primera = fecha_inicio o hoy, las siguientes espaciadas razonablemente.
- Si no sabés un monto, poné 0.
"""


def _build_user_prompt(obra: models.Obra, contexto: str) -> str:
    cliente = obra.cliente.nombre if obra.cliente else "sin cliente registrado"
    return (
        f"Obra: {obra.codigo} — {obra.nombre}\n"
        f"Cliente: {cliente}\n"
        f"Ciudad / Dirección: {obra.ciudad or obra.direccion or 'sin especificar'}\n"
        f"Monto contrato: ${float(obra.monto_contrato or 0):.0f}\n"
        f"Tipo facturación: {obra.tipo_facturacion.value}\n"
        f"Fecha inicio: {obra.fecha_inicio.isoformat() if obra.fecha_inicio else 'sin fecha'}\n"
        f"Fecha fin estimada: {obra.fecha_fin_estimada.isoformat() if obra.fecha_fin_estimada else 'sin fecha'}\n"
        f"Superficie: {obra.superficie_m2 or 0} m²\n"
        f"Pisos: {obra.pisos or 1}\n"
        f"\n--- CONTEXTO DEL USUARIO ---\n"
        f"{contexto}\n"
    )


def _placeholder_plan(obra: models.Obra, contexto: str) -> dict:
    """Plan determinístico para cuando no hay LLM disponible.

    Cubre el caso de tests y de dev sin API key. Cuatro etapas estándar.
    """
    fi = obra.fecha_inicio or date.today()
    monto = float(obra.monto_contrato or 0)
    etapas = [
        {
            "nombre": "Anticipo",
            "nro_etapa": 0,
            "monto_contractual": round(monto * 0.30, 2),
            "porcentaje_avance": 30,
            "fecha_estimada": fi.isoformat(),
            "notas": "Anticipo inicial al firmar contrato.",
        },
        {
            "nombre": "Etapa 1 — Cimientos y estructura",
            "nro_etapa": 1,
            "monto_contractual": round(monto * 0.30, 2),
            "porcentaje_avance": 30,
            "fecha_estimada": (fi + timedelta(days=60)).isoformat(),
            "notas": "Estructura completa y cubierta.",
        },
        {
            "nombre": "Etapa 2 — Cerramientos e instalaciones",
            "nro_etapa": 2,
            "monto_contractual": round(monto * 0.25, 2),
            "porcentaje_avance": 25,
            "fecha_estimada": (fi + timedelta(days=120)).isoformat(),
            "notas": "Mampostería, electricidad, plomería y gas.",
        },
        {
            "nombre": "Etapa 3 — Terminaciones y final",
            "nro_etapa": 3,
            "monto_contractual": round(monto * 0.15, 2),
            "porcentaje_avance": 15,
            "fecha_estimada": (fi + timedelta(days=180)).isoformat(),
            "notas": "Terminaciones, pintura, sanitarios y entrega.",
        },
    ]
    frentes = [
        {"nombre": "Cimientos", "tipo": "estructura", "notas": "Excavación y bases."},
        {"nombre": "Estructura", "tipo": "estructura", "notas": "Columnas, losas y techos."},
        {"nombre": "Mampostería", "tipo": "mamposteria", "notas": "Levantar paredes."},
        {"nombre": "Instalaciones", "tipo": "instalaciones", "notas": "Eléctrica, plomería, gas."},
        {"nombre": "Terminaciones", "tipo": "terminaciones", "notas": "Pintura, sanitarios, pisos."},
    ]
    materiales = [
        {"nombre": "Cemento", "categoria": "cemento", "unidad": "bolsa", "cantidad": 0, "etapa": "Etapa 1"},
        {"nombre": "Hierro 8mm", "categoria": "hierro", "unidad": "kg", "cantidad": 0, "etapa": "Etapa 1"},
        {"nombre": "Ladrillo común", "categoria": "ladrillo", "unidad": "u", "cantidad": 0, "etapa": "Etapa 2"},
        {"nombre": "Arena fina", "categoria": "áridos", "unidad": "m3", "cantidad": 0, "etapa": "Etapa 2"},
    ]
    return {
        "etapas": etapas,
        "frentes": frentes,
        "materiales_sugeridos": materiales,
        "notas_generales": (
            "Plan generado en modo offline (sin LLM). Editá los montos y fechas "
            "según los datos reales del proyecto. Contexto recibido: "
            + (contexto[:200] + "…" if len(contexto) > 200 else contexto)
        ),
    }


def _llm_plan(obra: models.Obra, contexto: str, model: str) -> tuple[dict, str]:
    """Llama a Claude. Devuelve (resultado_dict, model_used).

    Si la llamada falla por cualquier motivo, cae en placeholder y devuelve
    nombre 'placeholder'. El caller decide cómo mostrarlo.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return _placeholder_plan(obra, contexto), "placeholder"

    try:
        from anthropic import Anthropic
    except ImportError:
        logger.warning("[plan_obra] anthropic SDK no instalado; usando placeholder.")
        return _placeholder_plan(obra, contexto), "placeholder"

    try:
        client = Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(obra, contexto)}],
        )
        text = "".join(b.text for b in msg.content if hasattr(b, "text"))
        # Limpiar wrappers comunes (```json ... ```)
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text
            text = text.rsplit("```", 1)[0].strip()
            if text.startswith("json"):
                text = text[4:].strip()
        data = json.loads(text)
        return data, model
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[plan_obra] LLM call falló ({e}); usando placeholder.")
        return _placeholder_plan(obra, contexto), "placeholder"


def generar_plan(
    db, *, obra: models.Obra, contexto: str, user_id: int,
    model_override: Optional[str] = None,
) -> models.PlanObraBorrador:
    """Genera un borrador y lo persiste."""
    model = model_override or os.getenv("AGENT_MODEL", "claude-sonnet-4-5")
    resultado, model_used = _llm_plan(obra, contexto, model)
    borrador = models.PlanObraBorrador(
        obra_id=obra.id,
        prompt_input=contexto.strip(),
        resultado_json=json.dumps(resultado, ensure_ascii=False),
        model_used=model_used,
        created_by_id=user_id,
    )
    db.add(borrador); db.commit(); db.refresh(borrador)
    return borrador


def aplicar_plan(db, borrador: models.PlanObraBorrador, user=None) -> dict:
    """Crea EtapaObra y Frente reales según el resultado_json del borrador.

    Devuelve {'etapas_creadas': N, 'frentes_creados': M}. Es idempotente
    en el sentido de que un borrador 'aplicado' no se puede volver a aplicar.

    NO crea Materiales (solo se sugieren — el usuario decide si los carga manual).

    Si se pasa `user`, hereda is_demo del usuario en las nuevas filas (defensivo:
    el listener before_flush también lo haría, pero el patrón del proyecto es
    stampear manual, ver Sprints 13/14/17/22).
    """
    if borrador.estado != models.PlanObraEstado.borrador:
        raise ValueError(f"El borrador ya está en estado {borrador.estado.value}")

    from app.security import stamp_demo

    data = json.loads(borrador.resultado_json)
    obra_id = borrador.obra_id

    etapas_creadas = 0
    for et in data.get("etapas", []):
        fe = et.get("fecha_estimada")
        if fe:
            try:
                fe = date.fromisoformat(fe)
            except ValueError:
                fe = None
        nueva = models.EtapaObra(
            obra_id=obra_id,
            nombre=et.get("nombre", "Etapa sin nombre"),
            nro_etapa=et.get("nro_etapa", 0),
            monto_contractual=et.get("monto_contractual") or 0,
            porcentaje_avance=et.get("porcentaje_avance") or 0,
            estado=models.EtapaEstado.PENDIENTE,
            fecha_estimada=fe,
            notas=et.get("notas"),
        )
        if user is not None:
            stamp_demo(nueva, user)
        db.add(nueva); etapas_creadas += 1

    frentes_creados = 0
    for fr in data.get("frentes", []):
        nuevo = models.Frente(
            obra_id=obra_id,
            nombre=fr.get("nombre", "Frente sin nombre"),
            tipo=fr.get("tipo"),
            estado=models.FrenteEstado.pendiente,
            notas=fr.get("notas"),
        )
        if user is not None:
            stamp_demo(nuevo, user)
        db.add(nuevo); frentes_creados += 1

    from datetime import datetime
    borrador.estado = models.PlanObraEstado.aplicado
    borrador.aplicado_at = datetime.utcnow()
    db.commit()

    return {
        "etapas_creadas": etapas_creadas,
        "frentes_creados": frentes_creados,
        "materiales_sugeridos_count": len(data.get("materiales_sugeridos", [])),
    }
