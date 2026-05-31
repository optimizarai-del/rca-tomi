# Sprint 21 — Contabilidad blanco / negro por obra

> Estado: ✅ cerrado · suite pytest **160/160** verde

## Requisitos

Notas reunión 2026-05-20 + diagrama de la foto 2:

- **Flujo de caja** = ingresos / egresos.
- **2 cajas separadas**: Blanco (con factura) y Negro (informal).
- Para cada caja: Ingresos → cómo se pagó (efectivo, cheque, transferencia, cc); Egresos → pagos a proveedor con/sin factura, comprobante.
- "Lo que tenés − lo que se debe".
- **Todo pensado por obra** (decisión arquitectónica grabada en memoria: [[decision-todo-por-obra]]).
- **Sacar los gráficos** — la pestaña no usa visualizaciones SVG, solo tabla.

## Cómo se hizo

### T1 — Rama
Branch `sprint-21-contabilidad-blanco-negro` desde `sprint-15-proveedores`.

### T2 — Modelo

[backend/app/models.py](../../backend/app/models.py): extiende `MovimientoObra` (la tabla central que ya existe del Sprint AB) con 6 columnas:

```python
legalidad: LegalidadMovimiento ('blanco' | 'negro')   default blanco
cobro_pago_estado: CobroPagoEstado ('pendiente' | 'cobrado' | 'pagado')
fecha_cobro_pago: Date | null
iva_pct: Numeric(5,4) | null         # 0.21 = 21%
iibb_pct: Numeric(5,4) | null        # 0.03 = 3%
gastos_banco: Numeric(15,2)          default 0
```

**Por qué extender en vez de tabla nueva**: `MovimientoObra` ya tiene `obra_id`, `tipo` (INGRESO/EGRESO), `medio_pago`, `comprobante_id`, `proveedor_id`, etc. Sumar 6 columnas evita duplicar el modelo.

Migración Alembic [b4d6e8f0a2c1](../../backend/alembic/versions/b4d6e8f0a2c1_sprint_21_blanco_negro_por_obra.py).

### T3 — Endpoints

[backend/app/routers/movimientos.py](../../backend/app/routers/movimientos.py):

- `GET /api/movimientos?obra_id=&legalidad=&cobro_pago_estado=` — listado filtrable.
- `GET /api/movimientos/obra/{oid}/resumen-finanzas` — devuelve `FinanzasObraResumen` con las 2 cajas + consolidados:
  ```
  blanco/negro: { ingresos_cobrado, ingresos_pendiente, egresos_pagado, egresos_pendiente,
                  iva_total, iibb_total, gastos_banco_total,
                  neto_efectivo, saldo_compromiso }
  lo_que_tenes:    suma de neto_efectivo (cobrado − pagado)
  lo_que_se_debe:  suma de saldo_compromiso (por cobrar − por pagar)
  saldo_total:     lo_que_tenes + lo_que_se_debe
  ```
- `PATCH /api/movimientos/{mid}/finanzas` — patch parcial para "marcar cobrado/pagado" o cambiar legalidad sin reenviar todo el payload. Validaciones:
  - INGRESO no acepta `cobro_pago_estado='pagado'` (debe ser `cobrado`).
  - EGRESO no acepta `cobro_pago_estado='cobrado'` (debe ser `pagado`).
  - Si pasa a cobrado/pagado y no se especifica `fecha_cobro_pago`, defaults a hoy.
  - Si vuelve a pendiente, se borra la `fecha_cobro_pago`.
- Solo admin puede patchear (`require_admin`).

### T4 — Frontend

[frontend/src/pages/ObraDetail.jsx](../../frontend/src/pages/ObraDetail.jsx):

- Reemplaza `FinanzasTab` completo. **Elimina `FlujoChart`** (gráfico SVG semanal) — los gráficos cosméticos salen como pidió el usuario.
- Nuevo `FinanzasBlancoNegroTab`:
  - 4 BigStats arriba: Contrato · Lo que tenés · Lo que se debe · Saldo total.
  - 3 sub-tabs: **Blanco** / **Negro** / **Consolidado**. Cada uno muestra el `neto_efectivo` en el tab.
  - Stats por caja: cobrado, pagado, por cobrar, por pagar (+ IVA/IIBB/gastos banco en blanco).
  - Tabla de movimientos de esa caja con chips de estado y acciones inline:
    - **Cobrado / Pagado** (con `Check`) o **Reabrir** (con `Clock`).
    - **⇄** para cambiar blanco↔negro.
  - Sigue mostrando el descalce fiscal y la tabla de flujo proyectado (sin gráfico).

### T5 — Tests

[backend/tests/test_blanco_negro.py](../../backend/tests/test_blanco_negro.py) — 16 casos:

- Crear movimiento con defaults (blanco/pendiente).
- Crear movimiento negro.
- Filtro por `legalidad` y `cobro_pago_estado` en el listado.
- Resumen calcula correctamente neto y compromiso (caso con blanco+negro mezclados).
- Resumen calcula IVA, IIBB y gastos banco.
- Resumen 404 si la obra no existe.
- PATCH: marcar cobrado, marcar pagado, volver a pendiente borra fecha.
- PATCH valida: ingreso no acepta pagado, egreso no acepta cobrado.
- PATCH cambia legalidad.
- PATCH 404 si movimiento no existe.
- PATCH solo admin (403 para supervisor).
- Resumen solo incluye movimientos de la obra solicitada.

Suite total: **160/160 verde**.

## Cómo se usa

### Caso del día: Tomi quiere ver qué ya cobró y qué le falta de la obra IDS

1. `/obra/IDS` → tab **Finanzas**.
2. Mira los 4 BigStats: ya ve "Lo que tenés" y "Lo que se debe" consolidado.
3. Click en sub-tab **Blanco**: ve el desglose con IVA, IIBB.
4. En la tabla: por cada movimiento aparece chip "cobrado/pagado" o "pendiente".
5. Cuando le pagan el certificado de la etapa 2: click en **Cobrado** → se actualiza al instante.
6. Si una factura era informal: click en **⇄** → pasa a caja Negro.

### Cargar un movimiento ya cobrado de entrada

Crear con `POST /api/movimientos`:
```json
{
  "obra_id": 1, "fecha": "2026-05-20", "tipo": "INGRESO",
  "origen_ingreso": "ANTICIPO_CLIENTE", "monto": 500000,
  "medio_pago": "TRANSFERENCIA",
  "legalidad": "blanco",
  "cobro_pago_estado": "cobrado",
  "fecha_cobro_pago": "2026-05-20",
  "iva_pct": 0.21, "iibb_pct": 0.03
}
```

## Deuda pendiente

- **Conciliación bancaria**: el siguiente sprint (S22 según el nuevo plan) — importar extracto bancario y matchear automáticamente con los movimientos del lado blanco.
- **Editar `gastos_banco` por movimiento desde la UI**: hoy se pasa solo al crear. Si Tomi necesita corregir, hace falta un input en el modal o ampliar el PATCH.
- **Memoria de clientes** (S22 también) — guardar datos recurrentes para autocompletar al cargar movimientos.
- **Flujo proyectado proyecta solo los movimientos sin distinguir caja**: si Tomi quiere ver "flujo proyectado solo blanco", hay que extender el endpoint.
- **Vista global de finanzas**: queda en `/finanzas` la versión vieja. La decisión arquitectónica dice "todo por obra primero", así que la global la retocamos solo si hace falta.
