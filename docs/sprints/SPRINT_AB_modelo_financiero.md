# Sprint A+B — Modelo financiero RCA

> Commit: `b89ca39 feat(finanzas): Sprint A+B — modelo financiero RCA según doc`
> Estado: ✅ cerrado

## Requisitos

El modelo original de la plataforma estaba pensado como un "videojuego de obras": cada obra tenía `presupuesto_total` y `presupuesto_consumido`, los gastos se cargaban en una tabla `gastos` simple, y no había concepto de cliente, régimen fiscal, etapas de cobro ni comprobantes AFIP.

El cliente real de RCA aportó un documento técnico — *"Modelo de gestión de gastos de obra v1.0 — Mayo 2026"* — con un modelo financiero serio que necesitaba implementarse para que la plataforma sirviera como herramienta de gestión de una constructora real.

**Objetivo:** reemplazar el modelo simplificado por uno que refleje cómo se manejan realmente las obras en Argentina: clientes con régimen fiscal, etapas con monto contractual, una tabla central de movimientos con todos los ingresos/egresos, aportes de socios, comprobantes AFIP con CAE, y reglas de negocio R1–R5 documentadas.

## Cómo se hizo

### Tablas nuevas

En `backend/app/models.py`:

- **`RegimenFiscal`** — RI / Monotributo / Exento. Define alícuota IVA default, si aplica IIBB y Ganancias.
- **`Cliente`** — CUIT, razón social, dirección, régimen fiscal heredable.
- **`EtapaObra`** — divide cada obra en N etapas con monto contractual y estado.
  - Estados: `PENDIENTE → EN_EJECUCION → EJECUTADA → FACTURADA → COBRADA`.
- **`MovimientoObra`** — ★ **tabla central** del sistema. Cada fila es un INGRESO o EGRESO.
  - Reemplaza la tabla `gastos` (que se eliminó).
  - Campos clave: `tipo`, `origen_ingreso`, `categoria_egreso`, `medio_pago`, `nro_cheque`, `fecha_vto_cheque`, `comprobante_id`, `aporte_socio_id`, `estado` (CONFIRMADO/A_REVISAR), `hoja_fisica`.
- **`AporteSocio`** — préstamos internos con obligación de devolución.
- **`Comprobante`** — datos AFIP (FC_A/B/C, NC, ND, Recibo X, Remito) con CAE.
- **`RetencionSufrida`** — Ganancias, IIBB, IVA, SUSS.
- **`NotaObra`** — observaciones libres por obra o por movimiento.

### Tabla `Obra` modificada

- Se le agregaron `cliente_id`, `regimen_fiscal_id`, `tipo_facturacion`, `monto_contrato`.
- Se eliminó `presupuesto_total` y `presupuesto_consumido`.

### Enums nuevos

- `TipoFacturacion` (TOTAL_BLANCO/TOTAL_NEGRO/MIXTA/SIN_DEFINIR)
- `EtapaEstado` (5 estados)
- `TipoMovimiento` (INGRESO/EGRESO)
- `OrigenIngreso` (6 valores)
- `CategoriaEgreso` (7 valores)
- `MedioPago` (5 valores)
- `EstadoMovimiento` (CONFIRMADO/A_REVISAR)
- `EstadoDevolucion` (PENDIENTE/PARCIAL/TOTAL)
- `TipoComprobante` (9 tipos AFIP)
- `EstadoFiscal` (VALIDO/SIN_CAE/VENCIDO/ANULADO)
- `TipoRetencion` (4 tipos)
- Rol nuevo `super_admin` para no gatear prematuramente

### Reglas de negocio (R1–R5)

- **R1** — el saldo NO se filtra por estado del movimiento. `CONFIRMADO` y `A_REVISAR` cuentan igual:
  ```python
  saldo = SUM(INGRESO.monto) - SUM(EGRESO.monto)
  ```
  Ver `backend/app/routers/movimientos.py` función `saldo_obra`.

- **R2** — al crear un `AporteSocio`, automáticamente se genera un `MovimientoObra` espejo de tipo INGRESO con origen `APORTE_SOCIO_RCA`. Se hace en la misma transacción para garantizar consistencia. Ver `backend/app/routers/aportes.py:46`.

- **R3** — los cheques propios (`MedioPago.CHEQUE_PROPIO`) tienen dos fechas relevantes:
  - `fecha`: cuándo se libró el cheque (cuándo entra al saldo de la obra).
  - `fecha_vto_cheque`: cuándo se cobra realmente.
  El flujo proyectado usa `fecha_vto_cheque` para reflejar la salida real de caja. Ver `backend/app/routers/movimientos.py:140`.

- **R4** — descalce fiscal: cuando una obra tiene egresos con factura > ingresos con factura, hay crédito fiscal IVA pendiente. Endpoint `GET /api/movimientos/descalce-fiscal`. Ver `backend/app/routers/movimientos.py:224`.

- **R5** — cuando una etapa pasa a `COBRADA` y existen aportes de socio pendientes vinculados a esa etapa (`AporteSocio.etapa_reintegro_id == etapa.id`), el sistema crea automáticamente una `NotaObra` importante para alertar al admin que tiene que devolver el aporte.

### Routers nuevos

| Router | Endpoints clave |
|---|---|
| `clientes` | CRUD básico |
| `regimenes_fiscales` | listado |
| `etapas` | CRUD + cascada R5 al cambiar a COBRADA |
| `movimientos` | CRUD + `/obra/{id}/saldo` + `/flujo-caja` + `/flujo-proyectado` + `/cheques-a-vencer` + `/descalce-fiscal` |
| `aportes` | CRUD + R2 espejo + `/{id}/devolucion` con EGRESO espejo |
| `comprobantes` | CRUD AFIP con validación neto+IVA=total (±0.05) |

### Integración con el agente IA

Se sumaron 5 tools nuevas a las 11 originales del Sprint 1:
`listar_clientes`, `listar_etapas`, `listar_movimientos`, `saldo_obra`, `flujo_caja_obra`, `aportes_pendientes`, `cheques_a_vencer`, `descalce_fiscal`.

El system prompt se actualizó con contexto del modelo nuevo.

### Frontend

- **HUD** (top nav) refactoreado: ahora muestra saldo global, cheques a vencer, aportes pendientes (en lugar de "presupuesto consumido").
- **`Finanzas.jsx`** rehecha: 4 big numbers (contratado / ingresos / egresos / saldo), alertas de aportes y cheques, breakdown por categoría y por obra, lista de movimientos con badges (FC, A_REVISAR, +/-).
- **`WorldMap.jsx`** adaptado a `estado` y `monto_contrato`. Modal "Nueva obra" integra cliente + régimen fiscal + tipo de facturación.
- **`ObraDetail.jsx`** trae cliente del dashboard.

### Infra

- **`docker-compose.yml`** opcional para Postgres en puerto 5433 (evita choque con PG local).
- **`scripts/reset_db.py`** — drop all + recreate + seed. Funciona con SQLite o PG.
- **`.env.example`** con `DATABASE_URL` para SQLite (default) o PG.
- **Seed nuevo** realista:
  - 2 obras: IDS Domingo Savio (TOTAL_BLANCO, $12.5M, 4 etapas) y SP San Pedro (MIXTA, $8.2M, 3 etapas).
  - 13 movimientos de demo (anticipos, MO semanal, materiales con factura, subcontrato pagado con cheque).
  - 1 aporte de socio + ingreso espejo automático.
  - 1 cheque a vencer en 15 días.
  - 1 factura A con CAE.
- **Sistema de ramas:** `main` (estable) + `dev` (desarrollo).

## Cómo se usa

### Crear una obra completa de cero

```bash
TOKEN=$(curl -s -X POST http://localhost:8010/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@rca.com","password":"demo1234"}' | jq -r .access_token)

# 1. Crear cliente
CLIENTE_ID=$(curl -s -X POST http://localhost:8010/api/clientes \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"nombre":"Cliente Test","cuit":"30-11111111-1","tipo":"privado_ri","regimen_fiscal_id":1}' | jq -r .id)

# 2. Crear obra (hereda régimen del cliente)
OBRA_ID=$(curl -s -X POST http://localhost:8010/api/obras \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"codigo\":\"TST\",\"nombre\":\"Obra Test\",\"cliente_id\":$CLIENTE_ID,\"tipo_facturacion\":\"MIXTA\",\"monto_contrato\":5000000}" | jq -r .id)

# 3. Crear etapa anticipo
curl -s -X POST http://localhost:8010/api/etapas \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"obra_id\":$OBRA_ID,\"nombre\":\"Anticipo\",\"nro_etapa\":0,\"monto_contractual\":1500000}"

# 4. Registrar el cobro del anticipo
curl -s -X POST http://localhost:8010/api/movimientos \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"obra_id\":$OBRA_ID,\"fecha\":\"2026-05-01\",\"tipo\":\"INGRESO\",\"origen_ingreso\":\"ANTICIPO_CLIENTE\",\"concepto\":\"Anticipo cliente\",\"monto\":1500000,\"medio_pago\":\"TRANSFERENCIA\"}"

# 5. Ver el saldo
curl -s "http://localhost:8010/api/movimientos/obra/$OBRA_ID/saldo" -H "Authorization: Bearer $TOKEN"
# → {"obra_id": ..., "total_ingresos": 1500000, "total_egresos": 0, "saldo": 1500000}
```

### Endpoints de reportes

```bash
# Saldo de una obra
GET /api/movimientos/obra/{oid}/saldo

# Flujo de caja semanal
GET /api/movimientos/obra/{oid}/flujo-caja

# Flujo proyectado (incluye cheques a vencer + etapas estimadas)
GET /api/movimientos/obra/{oid}/flujo-proyectado?horizonte_dias=90

# Cheques propios a vencer en N días
GET /api/movimientos/cheques-a-vencer?dias=30

# Descalce fiscal (todas las obras o una)
GET /api/movimientos/descalce-fiscal[?obra_id=N]   # solo admin/finanzas
```

### Reset con datos demo realistas

```bash
cd backend
.venv/Scripts/python.exe -m scripts.reset_db
```

Después podés loguearte con `admin@rca.com / demo1234` y vas a ver las dos obras del seed (IDS y SP) con todos los movimientos.

## Tests realizados

- Crear obra TOTAL_BLANCO → intentar registrar INGRESO de cliente sin comprobante → backend rechaza con 400.
- Crear aporte de socio → verificar que automáticamente aparece un movimiento INGRESO espejo.
- Cambiar etapa con aporte pendiente a `COBRADA` → verificar que se creó una `NotaObra` importante (R5).
- Cargar comprobante con `neto + IVA != total` → backend rechaza con 400 explicando la diferencia.
- Devolución parcial de aporte → estado pasa a `DEVUELTO_PARCIAL`, EGRESO espejo creado, monto pendiente recalculado.
- Saldo con movimientos `A_REVISAR` mezclados con `CONFIRMADO` → R1: ambos cuentan en el saldo.

## Estado y deuda

✅ **Implementado:** todo el modelo del documento técnico — 11 tablas, 13 enums, 5 reglas R1–R5, routers y endpoints, agente IA actualizado, frontend mínimo funcional.

⚠️ **Notas de implementación:**
- Se usaron Integer PKs en vez de UUID (que el doc sugería) por compatibilidad con código previo. UUIDs como campo público se pueden agregar después sin breaking change.
- Las reglas (R1–R5) se implementaron con eventos SQLAlchemy y lógica en routers, no con triggers PostgreSQL — para mantener portabilidad SQLite ↔ PG.
- La capa lúdica vieja (cuadrillas, frentes, órdenes, eventos) se conservó como overlay opcional. **No contamina** los reportes financieros.

🛠️ **Deuda menor que quedó:**
- La columna `User.onboarding_step` no se usa en la UI (todavía).
- La tabla `herramientas_en_obra` está mencionada en el doc pero no implementada (espera el módulo de patrimonio).
- No hay tabla `Socio` propia: por ahora se usan `User` con rol `admin_finanzas` como proxy en `AporteSocio.socio_id`.

📌 **Punto de extensión usado después:** el modelo financiero quedó completo pero sin UI dedicada para crear/editar movimientos, aportes, comprobantes — eso lo cubrió el Sprint 3.
