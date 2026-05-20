# Sprint 14 — Estados de pedido / retirar / retirado + alertas

> Estado: ✅ cerrado · suite pytest **133/133** verde

## Requisitos

Notas de reunión 2026-05-19:

> MATERIALES — **EN DEPOSITO** (comprado, sobrante), **EN OBRAS** (qué obra),
> **PEDIDO** (retirar o retirado).
> RETIRAR → mostrar fecha y **1 día antes lanzar aviso** de que hay que retirar X material.
> RETIRADO → mostrar cuándo se retiró, **cómo se pagó** (foto de la factura) y **blanco/negro**, por obra.

El stock multi-ubicación ya existía desde Sprint 9 (`StockMaterial` con `deposito_propio` · `en_obra` · `comprado_no_retirado`). Lo que faltaba era:
1. Agendar fecha de retiro para los pendientes (`fecha_retirar`).
2. Alerta automática 1 día antes por Telegram.
3. Registrar el evento del retiro con detalle de pago, blanco/negro, comprobante.

## Cómo se hizo

### T1 — Rama

Branch `sprint-14-stock-retiros` desde `sprint-17-requerimientos`.

### T2 — Modelos

[backend/app/models.py](../../backend/app/models.py):

**StockMaterial** (extendido):
```python
fecha_retirar = Column(Date, index=True)         # solo aplica a comprado_no_retirado
retiro_alertado_at = Column(DateTime)            # dedupe de alertas
```

**RetiroMaterial** (nuevo, histórico):
```python
id, is_demo, material_id, proveedor_id, obra_destino_id, cantidad,
fecha_retiro, forma_pago (MedioPago enum), en_negro: bool,
comprobante_id (FK Comprobante, ya pensado para S18 OCR),
notas, created_by_id, created_at
```

Migración Alembic [a3c5d7e9f1b2](../../backend/alembic/versions/a3c5d7e9f1b2_sprint_14_retiros_material.py).

`retiros_material` agregada a `_DEMO_TABLES` para que herede el scoping demo.

### T3 — Servicio `stock.py`

[backend/app/stock.py](../../backend/app/stock.py) suma 4 funciones:

- `agendar_retiro(db, stock_material_id, fecha_retirar)` — setea fecha, resetea `alertado_at` (para rearmar la alerta si la fecha cambia).
- `marcar_retirado(db, stock_material_id, cantidad, fecha_retiro, forma_pago, en_negro, comprobante_id, destino_tipo, destino_obra_id, notas, usuario_id)` — operación atómica: baja `comprado_no_retirado`, sube destino, crea `RetiroMaterial`, registra en `movimientos_material`, recalcula cache `Material.stock`. Si la fila pendiente queda en 0, limpia `fecha_retirar` y `alertado_at`.
- `pendientes_retiro_proximos(db, dias=7, incluir_sin_fecha=False)` — query parametrizada.
- `listar_retiros(db, desde, hasta, obra_id, proveedor_id)` — histórico filtrado.

El `breakdown_por_material` ahora devuelve también `stock_material_id` (id de la fila) y `fecha_retirar` por ubicación, para que la UI pueda accionar sin tener que hacer otra query.

### T4 — Endpoints

[backend/app/routers/stock.py](../../backend/app/routers/stock.py):

- `GET /api/stock/pendientes?dias=&incluir_sin_fecha=` — lista filtrada para el panel.
- `GET /api/stock/retiros?desde=&hasta=&obra_id=&proveedor_id=` — histórico.
- `PATCH /api/stock/{sid}/agendar-retiro` — setea fecha.
- `POST /api/stock/{sid}/retirar` — registra el retiro con forma_pago/en_negro/comprobante.

⚠️ Los GET de paths fijos van **antes** de `/{material_id}` para no chocar (FastAPI matchea por orden).

### T5 — Alertas: `notificaciones.py` + script

[backend/app/notificaciones.py](../../backend/app/notificaciones.py):

```python
def notificar_retiros_pendientes(db, dias_antes=1) -> dict
```

Para cada `StockMaterial` con `fecha_retirar = today + dias_antes` y `retiro_alertado_at IS NULL`:
- Manda mensaje por Telegram a todos los admins con `telegram_chat_id`.
- Usa `send_telegram(..., notification_type="retiro_pendiente", context_key=..., dedupe=True)` — el sender ya hace dedupe por `context_key + user_id`.
- Marca `retiro_alertado_at = now()`.

Idempotente: si la fecha cambia, `agendar_retiro` resetea `alertado_at` y vuelve a poder dispararse.

[backend/scripts/notificar_retiros.py](../../backend/scripts/notificar_retiros.py): wrapper para cron.

Programar en Easy Panel o cron:
```cron
0 8 * * *  cd /app && python -m scripts.notificar_retiros
```

### T6 — Slash bot

[backend/app/slash_commands.py](../../backend/app/slash_commands.py):

```
/pendientes [dias]
```

Lista los pendientes de retiro dentro de N días (default 7), incluyendo los sin fecha agendada. Marca con chips: HOY · mañana · en Nd · vencido (-Nd).

### T7 — Frontend

[frontend/src/pages/Materiales.jsx](../../frontend/src/pages/Materiales.jsx):

- Nueva card **Pendientes de retiro** arriba de la tabla de materiales (solo si hay items).
- Por fila: nombre del material, cantidad, proveedor, chip de fecha (HOY/mañana/en Nd/vencido), input de fecha inline para agendar, botón **"Marcar retirado"**.
- Modal **Marcar retirado** con: cantidad (max=cantidad pendiente), fecha retiro, forma de pago (5 opciones), radio blanco/negro, destino (depósito propio / directo a obra + selector), notas.
- El input de fecha agenda en `onBlur` (sin botón explícito) para fricción mínima.

## Cómo se usa

### Flujo típico (caso del día)

1. **Bot WhatsApp**: el ayudante dice "compré 100 bolsas de cemento a Holcim" → agente IA crea fila `StockMaterial(comprado_no_retirado, cantidad=100, proveedor=Holcim)`.
2. **Web /materiales** → card "Pendientes de retiro" → seleccionar fecha en el input inline → queda agendado.
3. **Día anterior 8am**: cron corre `notificar_retiros` → llega push por Telegram a los admins:
   ```
   🚚 Mañana hay que retirar:
     • 100 bolsa de Cemento
     • Proveedor: Holcim
     • Fecha: 2026-06-15
   ```
4. **Día del retiro**: botón **"Marcar retirado"** en la web → modal pide cantidad/forma_pago/blanco-negro/destino → al confirmar baja `comprado_no_retirado` y crea fila `RetiroMaterial`.
5. **Histórico**: `GET /api/stock/retiros` muestra toda la trazabilidad con cómo se pagó cada retiro.

### Desde Telegram

```
/pendientes 7
```

Lista los próximos a vencer. El retiro efectivo se hace por la web (necesita forma de pago, destino, etc. — un slash sería muy largo).

## Tests

[backend/tests/test_retiros.py](../../backend/tests/test_retiros.py) — 18 casos:

- Agendar retiro (solo en pendientes, resetea alertado_at).
- Marcar retirado completo a depósito.
- Marcar retirado parcial directo a obra con en_negro=True.
- Cantidad mayor que disponible → error.
- `destino_tipo=en_obra` sin obra_id → error.
- `pendientes_retiro_proximos` filtra por fecha y por horizonte.
- `notificar_retiros_pendientes`: caso log_only, marca `alertado_at`, idempotente al re-ejecutar.
- Endpoints: pendientes, agendar-retiro, marcar-retirado, histórico.
- Slash `/pendientes`: con datos, sin datos, parámetro inválido.

Suite total: **133/133 verde**.

## Deuda pendiente

- **Foto de factura**: el campo `comprobante_id` ya existe en `RetiroMaterial`. Pero el flujo "sacar foto desde Telegram → crear Comprobante → linkear al retiro" se cierra en **Sprint 18 (OCR con Claude Vision)**. Hoy la foto se puede cargar manual creando un Comprobante por API y pasando su ID al endpoint `/retirar`.
- **Sobrante**: la nota original mencionaba "EN DEPOSITO (comprado, sobrante)". No diferenciamos comprado vs sobrante porque operacionalmente da igual (ambos están en `deposito_propio`). Si emerge la necesidad, agregar campo `origen` a la fila.
- **Alertar también al bot del proveedor / contacto externo**: por ahora la alerta es interna (admins). Si se quiere notificar también al proveedor, hay que extender `notificar_retiros_pendientes` con un canal alternativo.
- **Cancelar agenda**: hoy no hay botón para "desagendar" (setear `fecha_retirar=None`). Workaround: poner fecha lejana. Si molesta, agregar un endpoint DELETE.
