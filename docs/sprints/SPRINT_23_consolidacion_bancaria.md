# Sprint 23 — Consolidación bancaria

> Estado: ✅ cerrado · suite pytest **202/202** verde

## Requisitos

Prioridad #3 de la reunión 2026-05-20:

> Consolidación bancaria / flujo real.

Después de tener la caja blanco/negro (S21), necesitamos comparar lo que dice el extracto bancario contra los movimientos cargados en la plataforma. Diferencias = inconsistencias a revisar.

## Cómo se hizo

Flujo MVP:
1. Usuario sube un CSV exportado del home banking.
2. El frontend lo parsea, le pregunta qué columna es fecha / descripción / débito / crédito / saldo.
3. Backend persiste el extracto y cada línea como `MovimientoBancario`.
4. Endpoint de **sugerencias** propone `MovimientoObra` con mismo monto (`débito → EGRESO`, `crédito → INGRESO`) dentro de ±N días.
5. Usuario matchea cada línea con un movimiento de obra desde un dropdown.
6. Resumen muestra "lo que dice el banco vs lo conciliado" y la diferencia.

### T1 — Rama
Branch `sprint-23-consolidacion-bancaria` desde `sprint-24-planificacion-obra`.

### T2 — Modelos

[backend/app/models.py](../../backend/app/models.py):

```python
class Extracto:
    id, is_demo, banco, cuenta, periodo_desde, periodo_hasta,
    archivo_nombre, total_debe, total_haber, total_movs,
    created_by_id, created_at

class MovimientoBancario:
    id, is_demo, extracto_id (CASCADE), fecha, descripcion,
    debito, credito, saldo (opcional),
    hash_dedupe,           # fecha+desc+monto → evita duplicar líneas idénticas
    movimiento_obra_id,    # null = sin match; nullable FK a MovimientoObra
    conciliado_at, conciliado_by_id
```

Migración Alembic [e8fbc1d2a4f5](../../backend/alembic/versions/e8fbc1d2a4f5_sprint_23_consolidacion_bancaria.py). Ambas tablas en `_DEMO_TABLES` y `consolidacion` en el catálogo `SECCIONES` (permisos S13).

### T3 — Endpoints

[backend/app/routers/consolidacion.py](../../backend/app/routers/consolidacion.py):

- `GET  /api/extractos` — lista (require_finanzas).
- `POST /api/extractos` — crea con `movimientos: [{fecha, descripcion, debito, credito, saldo}]`. Dedupe interno por hash.
- `GET  /api/extractos/{eid}` — extracto + movimientos.
- `DELETE /api/extractos/{eid}` — admin only; cascadea movimientos.
- `GET  /api/extractos/{eid}/sugerencias?tolerancia_dias=7` — para cada `MovimientoBancario` sin match, propone hasta 5 `MovimientoObra` (mismo monto, tipo según débito/crédito, dentro de ventana ±N días, ordenados por distancia). Excluye los ya matcheados con otra línea.
- `GET  /api/extractos/{eid}/consolidacion` — resumen con `total_debe_extracto`, `total_haber_extracto`, `total_debe/haber_obra_conciliado` y `diferencia_debe/haber`.
- `POST /api/movimientos-bancarios/{mbid}/match` — vincula con `MovimientoObra`. Rechaza si esa obra ya está matcheada con otra línea (1↔1).
- `DELETE /api/movimientos-bancarios/{mbid}/match` — desvincula.

### T4 — Frontend

Nueva página [`/consolidacion`](../../frontend/src/pages/Consolidacion.jsx) (require_finanzas, item en sidebar sección Finanzas):

**Lista**: cards de extractos con `banco · cuenta`, periodo, totales y movs.

**Modal de import CSV** (3 pasos):
1. **Upload**: arrastrar archivo, parsea con separadores `, ; tab`.
2. **Mapping**: dropdowns para mapear columnas → fecha / descripción / débito / crédito / saldo. **Sugerencia automática** por nombre de header (regex de "fecha|date", "deb|salida", "cred|haber|entrada", etc.). Inputs para banco, cuenta, periodo.
3. **Preview**: tabla con primeras 30 filas parseadas. Botón "Importar N movs".
   - Parser de fechas soporta `YYYY-MM-DD`, `DD/MM/YYYY`, `DD-MM-YYYY`.
   - Parser de números soporta `1.234,56` (español) y limpia caracteres.

**Detalle**: `/consolidacion/:id` con 4+4 BigStats (débitos/créditos extracto y conciliado, totales y diferencias), filtro `Todos / Sin match / Conciliados`, tabla de movimientos con dropdown de sugerencias por fila.

### T5 — Tests

[backend/tests/test_consolidacion.py](../../backend/tests/test_consolidacion.py) — 12 casos:

- Crear extracto calcula totales (`total_debe`, `total_haber`, `total_movs`).
- Sin movimientos → 400.
- Dedupe: líneas idénticas se persisten una sola vez.
- Detalle devuelve movimientos.
- Sugerencias matchean por monto + tipo (débito→EGRESO) + ventana de fechas con `distancia_dias`.
- Sugerencias excluyen `MovimientoObra` ya matcheados con otra línea.
- Match crea relación + `conciliado_at`. Resumen post-match recalcula `total_debe_obra_conciliado` y `diferencia_debe`.
- Match doble (mismo `movimiento_obra_id` con dos líneas) → 400.
- Desvincular limpia FK y fecha.
- Delete del extracto cascadea movimientos.
- 404 en GETs con id inexistente.
- `require_finanzas`: admin sin finanzas no puede crear (403).

Suite total: **202/202 verde**.

## Cómo se usa

### Flujo típico mensual

1. Exportar CSV del home banking (Galicia / BBVA / Santander / etc.).
2. `/consolidacion` → **Importar extracto**.
3. Subir archivo, mapear columnas (en general las detecta solas), poner banco y periodo.
4. Click **Importar**.
5. Para cada línea sin match, abrir el dropdown — aparecen sugerencias filtradas por monto y fecha.
6. Seleccionar la `MovimientoObra` que corresponde → queda conciliado.
7. Los stats arriba muestran cuánto falta conciliar.

### Filtros del detalle
- **Sin match**: lo que falta atribuir.
- **Conciliados**: ya cruzados con un mov de obra.
- **Todos**: vista completa.

## Deuda pendiente

- **Parser CSV no soporta comas dentro de comillas en serio**: si el banco exporta descripciones con `"Pago a Empresa, SA"`, ese split rompe. Para MVP alcanza; mejorar con un parser CSV robusto (e.g. PapaParse) si se necesita.
- **Sugerencias por monto aproximado**: hoy es match exacto. Si el banco cobra una comisión que partió un cheque en 2 importes, no encuentra. Se podría agregar tolerancia ±X%.
- **Match por descripción**: si la descripción contiene CUIT o nombre de proveedor, se podrían sugerir matches por similitud de texto. No implementado.
- **Reimportar el mismo periodo**: el `hash_dedupe` está por extracto, no global. Si se sube dos veces el mismo CSV crea dos extractos separados (con sus propios movimientos). Si esto se vuelve molesto, agregar índice único global y rechazo.
- **Conciliación parcial**: hoy es 1↔1. Si un mov banco corresponde a 3 movs de obra (ej. consolidación de cobros), no se modela. Se puede agregar tabla `MatchN` después si emerge la necesidad.
- **Eliminar borradores demo**: el seed no crea extractos; el usuario los carga manualmente.
