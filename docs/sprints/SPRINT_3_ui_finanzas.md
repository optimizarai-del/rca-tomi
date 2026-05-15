# Sprint 3 — UI completa de gestión financiera

> Commit: `3a1bc5d feat(ui): Sprint 3 — UI completa de gestión financiera`
> Estado: ✅ cerrado

## Requisitos

El Sprint A+B implementó el modelo financiero completo en backend (clientes, etapas, movimientos, aportes, comprobantes, descalce fiscal) y todo era accesible vía REST y desde el agente IA. Pero la UI solo tenía la página `/finanzas` con un resumen simple — para crear/editar/ver entidades había que ir a Swagger o usar el agente.

**Objetivo:** UI completa de gestión financiera. Un admin tiene que poder gestionar clientes, movimientos, aportes y comprobantes sin tocar la API directamente, y ver el flujo de caja real y proyectado de cada obra.

## Cómo se hizo

### T0 — Bug fix preliminar

El seed nuevo crea al admin con role `super_admin`, pero `AuthContext.isAdmin` y `hasFinanzas` solo testaban contra `'admin'` y `'admin_finanzas'`. Resultado: con el seed nuevo el sidebar no mostraba Recursos, Finanzas ni Administración.

Fix en `frontend/src/context/AuthContext.jsx`:
```js
const isAdmin = ['super_admin', 'admin', 'admin_finanzas'].includes(user?.role)
const hasFinanzas = ['super_admin', 'admin_finanzas'].includes(user?.role)
```

También fix de un bug pre-existente en `ObraDetail.jsx` línea 77: usaba `dashboard?.cliente_nombre` cuando la variable es `data` — rompía la página entera.

### T1 — Sidebar refactoreado

`frontend/src/components/Layout/Sidebar.jsx`:

Antes la sección "Finanzas" tenía solo "Presupuestos". Ahora:

```
Finanzas
  $ Resumen          → /finanzas (vista global, ya existía)
  ⇆ Movimientos      → /movimientos        (nuevo, T2)
  💰 Aportes         → /aportes             (nuevo, T5)
  📄 Comprobantes    → /comprobantes        (nuevo, T6)
  🏢 Clientes        → /clientes            (nuevo, T4)
```

12 nav items totales en el sidebar para super_admin.

### T2 — Página `/movimientos` completa

`frontend/src/pages/Movimientos.jsx`:

- **Big numbers** (4): Ingresos, Egresos, Saldo (con color según signo), count.
- **Filtros** (8): Obra, Tipo, Categoría (revelado solo si tipo=EGRESO), Origen (solo si tipo=INGRESO), Medio de pago, Estado, Comprobante (sí/no), Desde, Hasta.
- **Tabla** con: fecha, obra (chip), tipo (chip olive/leather), concepto, monto (con color), medio, categoría/origen, comprobante (✓/—), estado.
- Filtros con backend: `obra_id`, `tipo`, `estado`, `desde`, `hasta` van a la query.
- Filtros locales (en memoria): categoría, origen, medio, comprobante.

### T3 — Modal "Nuevo movimiento" UX progresiva

Componente `<NuevoMovimientoModal>` dentro del mismo archivo. Los campos se revelan en steps:

1. **Tipo** (botones grandes con ícono): Ingreso (olive) / Egreso (leather).
2. **Obra + Etapa** (revelado al elegir tipo).
3. **Categoría/Origen** (revelado al elegir obra) — selector cambia según tipo.
4. **Monto + Concepto + Fecha** (revelado al elegir categoría/origen).
5. **Medio de pago** + cheque condicional (si CHEQUE_PROPIO/TERCERO, muestra nro/banco/vto en card destacada).
6. **Comprobante + Estado + Hoja física** (opcional, con warning si TOTAL_BLANCO+INGRESO de cliente exige FC).

El botón "Guardar" se habilita solo cuando todos los campos obligatorios están completos.

### T4 — Página `/clientes` (CRUD)

`frontend/src/pages/Clientes.jsx`:

- Cards (no tabla — más visual): tipo (eyebrow), nombre, razón social, CUIT/email/teléfono con íconos, chip de régimen, count de obras.
- Filtros pill por tipo (Público / Privado RI / Privado MT / Particular).
- Click en card → modal de edición con todos los campos + botón "Eliminar" (con `confirm()` nativo).
- Backend rechaza eliminar si tiene obras asociadas → mensaje claro.

### T5 — Página `/aportes`

`frontend/src/pages/Aportes.jsx`:

- 4 big numbers: total aportado, devuelto, pendiente, count.
- Filtros pill por estado (Todos / Pendientes / Parciales / Devueltos) + dropdown obra.
- Tabla con: fecha, obra, socio, motivo, monto, devuelto, pendiente, estado, [Registrar devolución].
- Modal de "Nuevo aporte" que avisa que va a crear un INGRESO espejo automático (R2).
- Modal de "Devolución" que pre-llena el monto pendiente, valida ≤ pendiente, y avisa que se va a crear un EGRESO espejo + actualizar el estado.

### T6 — Página `/comprobantes`

`frontend/src/pages/Comprobantes.jsx`:

- 4 big numbers: emitido (venta), recibido (compra), con CAE válido, sin CAE/vencidos.
- Filtros: obra, tipo (FC_A/B/C, NC, ND, etc), dirección (emitido/recibido), estado fiscal.
- Tabla con: fecha, obra, tipo+nro, dirección, CUIT (otra parte), neto, IVA, total, CAE, estado fiscal.
- Modal "Cargar comprobante" en 3 secciones:
  - Identificación (obra, tipo, dirección, punto venta, nro, fecha, CUITs)
  - Montos con auto-cálculo de total y warning en tiempo real si neto+IVA ≠ total
  - AFIP (CAE, vencimiento, estado fiscal)

### T7 — Tab Etapas en `ObraDetail`

Nueva tab dentro de `frontend/src/pages/ObraDetail.jsx`:

- Tabla de etapas ordenadas por `nro_etapa` con: nº, nombre, monto, % obra, **dropdown de estado** (cambia inline), fecha estimada, fecha cobro real.
- Cambiar estado dispara `PUT /api/etapas/{id}` que en el backend ejecuta R5 si pasa a COBRADA con aportes pendientes.
- Modal "Nueva etapa" simple con todos los campos.
- Footer con texto explicativo de la regla R5.

### T8 + T9 — Tab Finanzas en `ObraDetail` (gráficos)

Mismo archivo. Tab nueva "Finanzas":

- 4 big numbers: contrato, ingresos, egresos, saldo.
- **Gráfico SVG custom de flujo de caja semanal** (sin dependencia de recharts/nivo):
  - Barras dobles por semana: olive (ingresos) y leather (egresos).
  - Línea navy del saldo acumulado superpuesta.
  - Tooltips por hover (`<title>` SVG).
  - Grid horizontal con labels de monto.
- **Tabla de flujo proyectado** con dropdown de horizonte (30/60/90/180/365 días):
  - Movimientos reales + cheques a vencer + etapas estimadas.
  - Saldo proyectado acumulado con color según signo.
  - Chip por origen (Real / Cheque a vencer / Etapa estimada).

### T10 — Reporte de descalce fiscal

- En `ObraDetail` (tab Finanzas): card por obra individual con monto del descalce.
- En `/finanzas` (resumen global): sección nueva con descalce total + breakdown por obra. Si no hay descalce, mensaje verde "✓ Ninguna obra presenta descalce".

### Utilidades CSS

Se agregaron al `frontend/src/index.css`:
- `.input-base` y `.select-base` — inputs/selects compactos para modales (rounded-xl, padding y tipografía menor que `.input` original).

## Cómo se usa

### Para un usuario admin

Después de loguearse, el sidebar muestra la sección **Finanzas** con 5 items:

1. **Resumen** (`/finanzas`) — vista global con big numbers, alertas, descalce global, breakdown por categoría y obra.
2. **Movimientos** (`/movimientos`) — tabla central. Botón "Nuevo movimiento" → modal con UX progresiva.
3. **Aportes** (`/aportes`) — préstamos internos. Botón "Registrar devolución" en cada fila pendiente.
4. **Comprobantes** (`/comprobantes`) — facturas/NC/ND. Botón "Cargar comprobante" con auto-validación.
5. **Clientes** (`/clientes`) — cards con CRUD.

Click en una obra desde el WorldMap abre `/obra/:id` con 6 tabs:
- Resumen | **Finanzas** | **Etapas** | Frentes | Órdenes | Actividad

### Cambiar el estado de una etapa

Ir a `/obra/:id` → tab "Etapas" → click en el dropdown de estado de la fila → seleccionar nuevo. El backend valida la transición y ejecuta R5 si aplica (crea nota automática si pasa a COBRADA con aportes pendientes).

### Ver el flujo de caja semanal de una obra

Ir a `/obra/:id` → tab "Finanzas" → la primera sección muestra el gráfico SVG con todas las semanas que tienen movimientos.

### Ver descalce fiscal

- **Global**: `/finanzas` → sección "Descalce fiscal" con total + breakdown.
- **Por obra**: `/obra/:id` → tab "Finanzas" → si la obra tiene descalce, aparece una card amarilla con el detalle.

## Tests realizados

Suite Playwright E2E sobre las 6 páginas + tabs de ObraDetail:

| Tarea | Test |
|---|---|
| T0 | Sidebar muestra 12 items con super_admin |
| T1 | 12 nav items, navegación a /movimientos OK |
| T2 | Filtro tipo=EGRESO revela "Categoría", 11 filas filtradas, big numbers actualizados |
| T3 | Modal abre, completar 5 steps, guardar → fila nueva en tope, big numbers +12.5k egresos |
| T4 | Crear cliente → 4 cards, click → editar → eliminar → 3 cards |
| T5 | Devolución parcial $200k de $600k → estado "Devuelto parcial", big numbers actualizados |
| T6 | Cargar comprobante → big numbers $460k → $581k recibido |
| T7 | Cambiar estado etapa EJECUTADA → FACTURADA persiste |
| T8 | SVG renderizado con barras y línea, big numbers correctos |
| T9 | 14 items en flujo proyectado |
| T10 | Card de descalce visible con $460k IDS |
| T11 | Smoke test recorriendo 6 páginas sin errores en consola |

7 screenshots de evidencia en `docs/screenshots/t2_*` a `t8_t9_*`.

## Estado y deuda

✅ **Cerrado:** UI completa de gestión financiera funcionando. 11 tareas + 1 fix preliminar = 12 ítems del sprint completados y testeados.

⚠️ **Detalles menores:**
- El gráfico SVG es custom (sin recharts) — funciona pero si en el futuro hace falta más complejidad (zoom, multi-axis), conviene migrar a recharts o nivo.
- El delete de cliente en la UI usa `window.confirm()` nativo — para mejor UX se podría reemplazar por un modal.
- Los big numbers de la página `/movimientos` se calculan sobre los movimientos filtrados en memoria (no global).

📌 **Cómo se conecta con otros sprints:**
- Las páginas creadas en este sprint son la "vista admin" de las acciones que el agente IA del Sprint 2 puede ejecutar — el usuario puede hacer todo desde la UI o pidiéndoselo al agente, los datos resultantes son los mismos.
- Sprint 4 sumó la página `/mensajes` siguiendo el mismo patrón de tabla + filtros + big numbers.
