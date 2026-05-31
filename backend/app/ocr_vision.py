"""Sprint 18 — Parsing de fotos de facturas/tickets con Claude Vision.

Recibe una imagen (URL pública o bytes), llama a Claude con un system prompt
que pide JSON estructurado y devuelve un dict.

Si no hay ANTHROPIC_API_KEY o falla el llamado, devuelve un placeholder
determinístico para que el sprint sea testeable sin API.

Estructura del JSON esperado:
    {
      "tipo_documento": "FC_A" | "FC_B" | "FC_C" | "RECIBO_X" | "TICKET" | "REMITO" | "NC_A" | ...,
      "nro_comprobante": "0001-00000123",
      "punto_venta": 1,
      "fecha_emision": "2026-05-20",
      "proveedor_nombre": "...",
      "proveedor_cuit": "30-12345678-9",
      "items": [
        {"descripcion": "...", "cantidad": 0, "unidad": "u", "precio_unitario": 0, "subtotal": 0}
      ],
      "neto_gravado": 0,
      "iva_21": 0,
      "iva_105": 0,
      "total": 0,
      "notas": "..."
    }
"""
from __future__ import annotations
import base64
import json
import logging
import os
from typing import Optional, Tuple
import httpx

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Sos un OCR de comprobantes de obra. Recibís UNA imagen de una factura,
ticket, recibo o remito argentino y devolvés JSON estructurado con TODA la información extraída.

DEVOLVÉ SOLO JSON, sin texto extra, sin markdown.

Campos a extraer:
- tipo_documento: uno de FC_A, FC_B, FC_C, NC_A, NC_B, ND_A, ND_B, RECIBO_X, REMITO, TICKET, OTRO.
- punto_venta: int (los 4-5 dígitos antes del guion del nro).
- nro_comprobante: string del nro completo ej "0001-00000123" o solo "00000123" si no hay PV.
- fecha_emision: ISO "YYYY-MM-DD".
- proveedor_nombre: razón social del emisor.
- proveedor_cuit: con guiones "30-12345678-9", si no se ve dejar null.
- items: array de líneas con descripción, cantidad, unidad (u, kg, m, m2, m3, etc.), precio_unitario, subtotal.
  Si no hay desglose por items (ej. ticket de paso), devolver array vacío.
- neto_gravado: numérico, sin IVA.
- iva_21: numérico.
- iva_105: numérico (alícuota 10.5).
- total: numérico, el TOTAL final.
- notas: texto libre con info que no entra en los campos anteriores (CUIT receptor, condición de venta, etc.) — máximo 200 chars.

REGLAS:
- Los montos en pesos argentinos. Limpiá separadores ("$ 1.234,56" → 1234.56).
- Si un campo no es legible o no aplica, devolvé null (no "" ni 0 si no estás seguro).
- Si la imagen no es un comprobante, devolvé tipo_documento="OTRO" y notas explicando.
- No inventes datos. Mejor null que adivinar.
"""


def _build_image_block(image_url: Optional[str], image_bytes: Optional[bytes], mime: str = "image/jpeg") -> dict:
    """Construye el bloque de imagen para messages.create de Anthropic.

    Prefiere bytes (base64) sobre URL — funciona mejor con URLs de Telegram que
    expiran rápido.
    """
    if image_bytes is not None:
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime,
                "data": base64.standard_b64encode(image_bytes).decode("ascii"),
            },
        }
    return {
        "type": "image",
        "source": {"type": "url", "url": image_url},
    }


def _placeholder_result(image_url: Optional[str]) -> dict:
    """Resultado determinístico para tests/dev sin API key."""
    return {
        "tipo_documento": "FC_A",
        "punto_venta": 1,
        "nro_comprobante": "0001-00000999",
        "fecha_emision": "2026-05-20",
        "proveedor_nombre": "Proveedor placeholder",
        "proveedor_cuit": None,
        "items": [
            {"descripcion": "Item demo", "cantidad": 1, "unidad": "u",
             "precio_unitario": 100, "subtotal": 100},
        ],
        "neto_gravado": 100,
        "iva_21": 21,
        "iva_105": 0,
        "total": 121,
        "notas": f"OCR offline placeholder. URL recibida: {image_url or '(bytes)'} ",
    }


def _download_image(url: str, timeout: float = 15.0) -> Optional[Tuple[bytes, str]]:
    """Descarga la imagen. Devuelve (bytes, mime) o None si falla."""
    try:
        r = httpx.get(url, timeout=timeout)
        r.raise_for_status()
        mime = r.headers.get("content-type", "image/jpeg").split(";")[0].strip()
        return r.content, mime
    except Exception as e:
        logger.warning(f"[ocr_vision] no pude descargar {url}: {e}")
        return None


def parsear_ticket(
    *,
    image_url: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    mime: str = "image/jpeg",
    model_override: Optional[str] = None,
) -> Tuple[dict, str]:
    """Llama a Claude Vision (si está configurado) y devuelve (dict, model_used).

    Si no hay API key o falla, devuelve placeholder y model_used='placeholder'.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    model = model_override or os.getenv("AGENT_MODEL", "claude-sonnet-4-5")

    if not api_key:
        return _placeholder_result(image_url), "placeholder"

    try:
        from anthropic import Anthropic
    except ImportError:
        logger.warning("[ocr_vision] anthropic SDK no disponible; placeholder.")
        return _placeholder_result(image_url), "placeholder"

    # Si vino URL pero no bytes, intentamos descargar (para evitar problemas
    # con URLs efímeras como las de Telegram).
    if image_bytes is None and image_url:
        downloaded = _download_image(image_url)
        if downloaded:
            image_bytes, mime = downloaded

    try:
        client = Anthropic(api_key=api_key)
        image_block = _build_image_block(image_url, image_bytes, mime)
        msg = client.messages.create(
            model=model,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": [image_block, {"type": "text", "text": "Extrae los datos del comprobante."}]},
            ],
        )
        text = "".join(b.text for b in msg.content if hasattr(b, "text")).strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text
            text = text.rsplit("```", 1)[0].strip()
            if text.startswith("json"):
                text = text[4:].strip()
        data = json.loads(text)
        return data, model
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ocr_vision] llamada fallida ({e}); usando placeholder.")
        return _placeholder_result(image_url), "placeholder"


# ─── Helpers para confirmación ─────────────────────────────────────────


def matchear_proveedor(db, cuit: Optional[str], nombre: Optional[str]):
    """Busca un Proveedor por CUIT (preferido) o por similitud de nombre.

    Devuelve la instancia o None.
    """
    from app import models

    if cuit:
        c = (cuit or "").strip()
        # match exacto
        p = db.query(models.Proveedor).filter(models.Proveedor.cuit == c).first()
        if p:
            return p
        # ignorar guiones
        c_compact = c.replace("-", "")
        for p in db.query(models.Proveedor).filter(models.Proveedor.cuit.isnot(None)).all():
            if (p.cuit or "").replace("-", "") == c_compact:
                return p

    if nombre:
        n = nombre.strip().lower()
        # contains case insensitive (toma el primero)
        for p in db.query(models.Proveedor).all():
            if n and n in (p.nombre or "").lower():
                return p
            if n and (p.nombre or "").lower() in n:
                return p
    return None


def tipo_comprobante_from_str(s: Optional[str]):
    """Mapea string libre a enum TipoComprobante. Default FC_C."""
    from app import models

    if not s:
        return models.TipoComprobante.FC_C
    s = str(s).strip().upper().replace(" ", "_")
    for tc in models.TipoComprobante:
        if tc.value == s or tc.name == s:
            return tc
    return models.TipoComprobante.FC_C
