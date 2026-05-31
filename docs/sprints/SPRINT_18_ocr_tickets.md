# Sprint 18 — OCR de tickets con Claude Vision

> Estado: ✅ cerrado · suite pytest **220/220** verde

## Requisitos

Notas reunión 2026-05-19:

> Que pueda sacar fotos de ticket, factura o comprobante, etc. para poder sacar datos de ahí y actualizar en la plataforma.

Cierra el ciclo bot → DB: la foto entra por Telegram, Claude Vision la parsea, se persiste un borrador (`TicketOCR`), Tomi confirma con `/confirmar` y se crea automáticamente el `Comprobante` + el `MovimientoObra` enlazado a la obra, proveedor (matching automático por CUIT/nombre), legalidad y forma de pago elegidos.

## Cómo se hizo

### T1 — Rama
Branch `sprint-18-ocr-tickets` desde `sprint-23-consolidacion-bancaria`.

### T2 — Modelo

[backend/app/models.py](../../backend/app/models.py):

```python
class TicketOCREstado(str, Enum):
    pendiente = "pendiente"
    confirmado = "confirmado"
    rechazado = "rechazado"
    error = "error"

class TicketOCR(Base):
    id, is_demo,
    telegram_chat_id, telegram_message_id, telegram_file_id, imagen_url_cached,
    resultado_json: Text,    # estructura parseada por Vision
    model_used: String(60),  # "claude-sonnet-4-5" | "placeholder"
    error_msg: Text,
    estado: TicketOCREstado,
    obra_id (FK), comprobante_id (FK), movimiento_obra_id (FK),
    created_by_id, created_at, confirmed_at
```

Migración Alembic [f1a3c5e7b9d2](../../backend/alembic/versions/f1a3c5e7b9d2_sprint_18_ocr_tickets.py). `tickets_ocr` agregado a `_DEMO_TABLES` y a `SECCIONES` (permisos S13).

### T3 — Servicio `ocr_vision.py`

[backend/app/ocr_vision.py](../../backend/app/ocr_vision.py):

- **`SYSTEM_PROMPT`** que pide JSON estricto con: `tipo_documento, nro_comprobante, punto_venta, fecha_emision, proveedor_nombre, proveedor_cuit, items[], neto_gravado, iva_21, iva_105, total, notas`.
- **`parsear_ticket(image_url|image_bytes)`**: llama a Claude `messages.create` con bloque `image` (URL o base64). Limpia wrappers `\`\`\`json` y parsea.
- **Fallback determinístico**: si no hay `ANTHROPIC_API_KEY`, falla la descarga, o el SDK no está disponible, devuelve un placeholder con `model_used="placeholder"`. Permite tests y dev sin API real.
- **`matchear_proveedor(db, cuit, nombre)`**: busca por CUIT exacto, después por CUIT sin guiones, después por contains de nombre. Devuelve `Proveedor | None`.
- **`tipo_comprobante_from_str`**: mapea string libre al enum `TipoComprobante`, default `FC_C`.

### T4 — Endpoints REST

[backend/app/routers/ocr_tickets.py](../../backend/app/routers/ocr_tickets.py):

- `POST /api/ocr-tickets/parse-now {image_url | image_base64}` — sube imagen, llama a Vision, persiste `TicketOCR`. (require_finanzas)
- `GET  /api/ocr-tickets?estado=` — lista filtrable.
- `GET  /api/ocr-tickets/{tid}` — detalle con resultado tipado.
- `POST /api/ocr-tickets/{tid}/confirmar {obra_id, proveedor_id?, es_venta, categoria_egreso, legalidad, medio_pago, cobro_pago_estado, notas_extra}` — crea `Comprobante` + `MovimientoObra` y deja el ticket en `confirmado`.
- `POST /api/ocr-tickets/{tid}/rechazar` — marca rechazado.
- `DELETE /api/ocr-tickets/{tid}` — hard delete (admin).

El `confirmar` resuelve el proveedor: si vino `proveedor_id` lo usa, si no, intenta match automático por CUIT/nombre del OCR.

### T5 — Bot Telegram

[backend/app/routers/telegram.py](../../backend/app/routers/telegram.py):

Antes el bot rechazaba fotos con un mensaje "todavía no las proceso". Ahora cuando llega `message.photo`:

1. Valida whitelist + vinculación de usuario (igual que para texto).
2. Toma `file_id` de mayor resolución del array `photo`.
3. Descarga URL temporal con `get_file_url(file_id)` (sender de S11).
4. Llama a `ocr_vision.parsear_ticket(image_url=...)`.
5. Persiste `TicketOCR` con `persistir_resultado(...)` (helper compartido con el router REST).
6. Match automático del proveedor.
7. Responde con un resumen formateado:

```
🧾 Ticket #N extraído (modelo: claude-sonnet-4-5)
  • Tipo: FC_A
  • Nro: 0012-00045678
  • Fecha: 2026-05-29
  • Proveedor: Holcim Argentina SA ✅ (match #1)
  • TOTAL: $800000.00

Para confirmarlo:
  /confirmar <N> <obra_codigo>
  /rechazar <N>
```

### T6 — Slash commands

[backend/app/slash_commands.py](../../backend/app/slash_commands.py):

- `/pendientes_ocr` — lista los tickets pendientes (id, nro, proveedor, total).
- `/confirmar <ticket_id> <obra_codigo>` — confirma el ticket usando defaults razonables (egreso, blanco, transferencia, pendiente). Para personalizar (cambiar a venta, blanco/negro, etc.) hay que usar la UI web o el endpoint REST.
- `/rechazar <ticket_id>` — marca rechazado.

`/help` actualizado.

### T7 — Frontend

[frontend/src/pages/OcrPendientes.jsx](../../frontend/src/pages/OcrPendientes.jsx) (`/ocr-tickets`, ítem **Tickets OCR** en sidebar, sección Finanzas):

- Filtros por estado: Pendientes / Confirmados / Rechazados / Con error.
- Lista de cards plegables — cada una muestra:
  - Imagen original cacheada (si la URL todavía está viva).
  - Tabla de items extraídos.
  - Campos clave: neto, IVA 21%, IVA 10.5%, **TOTAL** destacado, CUIT proveedor.
  - Notas del LLM.
- Si el ticket está **pendiente**:
  - Form con selects: Obra (obligatorio), Proveedor (override del match), Legalidad (blanco/negro), Medio de pago, Estado cobro/pago, Es venta (checkbox).
  - Botones **Confirmar** / **Rechazar**.
- Si está **confirmado**: muestra los IDs del comprobante y movimiento generados.
- Si está **error**: muestra `error_msg`.
- **Modal "Subir foto"** desde la web: file picker (encoded a base64) o URL pública. Útil para probar sin Telegram.

### T8 — Tests

[backend/tests/test_ocr_tickets.py](../../backend/tests/test_ocr_tickets.py) — 18 casos, forzando `ANTHROPIC_API_KEY=""` para usar placeholder:

- `parsear_ticket` devuelve placeholder con estructura conocida.
- POST `parse-now` con URL y con base64; 400 sin imagen.
- Listar filtrado por estado.
- Confirmar crea Comprobante + MovimientoObra (con `canal=agente_ia`, `proveedor_id` matcheado por CUIT, `legalidad=blanco` por default).
- Confirmar dos veces → 400.
- Obra inexistente → 400.
- Rechazar marca estado.
- No se puede confirmar uno rechazado.
- Delete (admin).
- Match de proveedor por CUIT exacto, sin guiones, por contains de nombre, sin match.
- Slash `/pendientes_ocr`, `/confirmar`, `/rechazar`.

Suite total: **220/220 verde**.

## Cómo se usa

### Desde Telegram (flujo principal)

1. Tomi saca foto de la factura con el celular y la manda al bot.
2. Bot responde con el resumen y un id de ticket.
3. Tomi escribe `/confirmar 7 IDS` → se crea el `Comprobante` y el `MovimientoObra` en obra IDS.
4. El movimiento aparece automáticamente en:
   - `/obra/IDS` tab Finanzas (caja Blanco, pagado).
   - `/proveedores/Holcim` historial (después del fix S15 de hoy).
   - `/clientes/...` si fuera venta.
   - `/consolidacion/:id` cuando se importe el extracto.

### Desde la web (alternativa)

`/ocr-tickets` → **Subir foto** → elegir archivo → backend parsea → aparece en la lista de pendientes con preview de la imagen y campos editables.

### Variables de entorno

```env
ANTHROPIC_API_KEY=sk-ant-api03-...   # opcional, sin esto usa placeholder
AGENT_MODEL=claude-sonnet-4-5         # default
```

## Deuda pendiente

- **Persistencia de la imagen**: hoy solo guardamos `imagen_url_cached` (URL temporal de Telegram ~1h). Para producción conviene copiarla a S3/Supabase Storage y guardar la URL persistente. La columna `Comprobante.archivo_url` ya queda con esa URL al confirmar.
- **CUIT receptor hardcodeado**: al crear el `Comprobante` se pone `cuit_receptor="30-99999999-9"`. Hay que leerlo de la config de RCA. (Sprint 20 cuando hagamos handoff a Tomi).
- **Edición del resultado antes de confirmar**: hoy si el OCR se equivoca en un campo (ej. total mal), no se puede corregir desde la UI sin re-parsear. Agregar PATCH del `resultado_json`.
- **Subir foto adjunta al webhook con caption**: si el usuario manda foto + caption `"obra=IDS"`, podríamos confirmar directo. No implementado.
- **Multi-página**: facturas largas con varias páginas requieren múltiples imágenes. Hoy una foto → un ticket. Posible extensión: agrupar por `caption` o por `media_group_id` de Telegram.
- **Costo de Vision**: cada llamada a Claude Sonnet con imagen consume tokens significativos. Loguearlo en `AgentAction` o en una tabla de cost tracking sería útil cuando esté Tomi en prod.
