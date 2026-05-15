# Auditoría responsive — 2026-05-13

Testeo manual con Playwright sobre 3 viewports. Capturas en [screenshots/responsive/](screenshots/responsive/).

| Viewport | Resolución | Estado | Detalle |
|---|---|---|---|
| Mobile | 375×667 | ❌ Roto | Sidebar fijo 240px tapa 64% del viewport; tablas no entran; títulos truncados |
| Notebook | 1280×800 | ✅ OK | 8 páginas verificadas. Bug `NaN%` detectado y arreglado durante el test |
| Desktop | 1920×1080 | ✅ OK | Contenido se centra a `max-w-[1400px]`, queda underuse aceptable a los costados |

## ✅ Bugs arreglados durante la auditoría

### 1. `NaN%` en `/obra/:id` → "PRESUPUESTO"

**Síntoma:** En el header de detalle de obra, la big stat "Presupuesto" mostraba `NaN%`.

**Causa:** [frontend/src/pages/ObraDetail.jsx:119](../frontend/src/pages/ObraDetail.jsx#L119) leía `data.presupuesto_pct`, pero el endpoint `GET /api/obras/:id/dashboard` nunca devuelve ese campo (las claves reales son `monto_contrato`, `total_egresos`, `total_ingresos`, …).

**Fix:** Calcular el porcentaje en el cliente con guard de división por cero:
```js
const presupuesto_pct = Number(data.monto_contrato) > 0
  ? (Number(data.total_egresos) / Number(data.monto_contrato)) * 100
  : 0
```
Ver [ObraDetail.jsx:63-66](../frontend/src/pages/ObraDetail.jsx#L63-L66).

**Verificado:** "PRESUPUESTO 24% consumido" en notebook + desktop, sin `NaN` en el DOM.

## 🚨 Issues pendientes — Mobile (375×667)

Estos no se pueden arreglar con un toque puntual: requieren un sprint de responsive enfocado.

| # | Issue | Impacto | Fix recomendado |
|---|---|---|---|
| M1 | Sidebar `w-60` (240px) siempre visible → tapa 64% del ancho en 375px | 🔴 Crítico | Convertir a drawer con hamburger en `< md` (Tailwind breakpoint). `aside` con `hidden md:flex`; agregar `<button>` con `lucide-react/Menu` en el topbar |
| M2 | Topbar HUD ("SALDO $1.2M · OBRAS 2 · CHEQUES $850k · APORTES $600k") no entra en 375px | 🟠 Alto | Colapsar a un solo `$1.2M` con tap → dropdown con el resto. O esconder en `< sm` |
| M3 | Hero titles (`text-5xl`/`text-6xl`) parten en 3 letras por línea (`Mov`, `Apo`, …) | 🟠 Alto | Reducir size con clamp: `text-3xl sm:text-4xl md:text-5xl lg:text-6xl` |
| M4 | Tablas de Movimientos / Comprobantes ilegibles (10+ columnas en 375px) | 🟠 Alto | En `< md`: render alternativo de **cards** apiladas (label arriba, value abajo) o `overflow-x-auto` con sticky first column |
| M5 | Botones "+ Nuevo movimiento" / "+ Nuevo cliente" se cortan | 🟡 Medio | `flex-wrap` en el header + `text-sm` en mobile |
| M6 | Page titles cortados ("Mov…" en vez de "Movimientos") | 🟡 Medio | El title hereda el size del hero — se resuelve junto con M3 |

## 🟡 Issues menores — Desktop / Notebook

| # | Issue | Sugerencia |
|---|---|---|
| D1 | En 1920×1080 el contenido se queda en `max-w-[1400px]` y los costados quedan vacíos | Aceptable para el lenguaje minimal Apple. Si se quiere usar más ancho, subir a `max-w-[1600px]` en tablas (movimientos / comprobantes). |
| D2 | `obras_pct`, `progreso` cuando obra recién creada → `0%` literal (no NaN). | Aceptable. |

## Páginas verificadas

Notebook 1280×800 (todas ✅):

- [/world](screenshots/responsive/notebook_world.png)
- [/obra/1](screenshots/responsive/notebook_obra1_overview.png), [Etapas](screenshots/responsive/notebook_obra1_etapas.png), [Finanzas](screenshots/responsive/notebook_obra1_finanzas2.png)
- [/movimientos](screenshots/responsive/notebook_movimientos.png)
- [/aportes](screenshots/responsive/notebook_aportes.png)
- [/comprobantes](screenshots/responsive/notebook_comprobantes.png)
- [/clientes](screenshots/responsive/notebook_clientes.png)
- [/socios](screenshots/responsive/notebook_socios.png)
- [/finanzas](screenshots/responsive/notebook_finanzas.png)
- [/ordenes](screenshots/responsive/notebook_ordenes.png)
- [/feed](screenshots/responsive/notebook_feed.png)
- [/cuadrillas](screenshots/responsive/notebook_cuadrillas.png)
- [/equipo](screenshots/responsive/notebook_equipo.png)

Desktop 1920×1080 (todas ✅):

- [/world](screenshots/responsive/desktop_world.png)
- [/obra/1 (con fix)](screenshots/responsive/desktop_obra1_fixed.png)
- [/movimientos](screenshots/responsive/desktop_movimientos.png)
- [/aportes](screenshots/responsive/desktop_aportes.png)
- [/comprobantes](screenshots/responsive/desktop_comprobantes.png)
- [/clientes](screenshots/responsive/desktop_clientes.png)
- [/socios](screenshots/responsive/desktop_socios.png)
- [/finanzas](screenshots/responsive/desktop_finanzas.png)
- [/feed](screenshots/responsive/desktop_feed.png)

Mobile 375×667 (❌ con issues):

- [/login](screenshots/responsive/mobile_login.png) — OK (no tiene sidebar)
- [/world](screenshots/responsive/mobile_world.png) — sidebar tapa todo
- [/obra/1](screenshots/responsive/mobile_obra1.png) — hero/título truncado
- [/movimientos](screenshots/responsive/mobile_movimientos.png) — tabla inutilizable
- [/finanzas](screenshots/responsive/mobile_finanzas.png) — big numbers no entran
- [/clientes](screenshots/responsive/mobile_clientes.png) — cards funcionan, sidebar tapa

## Recomendación

**Cerrar como aceptable para desktop + notebook** y abrir un **Sprint 9 — Mobile responsive** para los issues M1–M6. El producto está pensado para administradores en escritorio (foreman / PM / socio finanzas); el caso mobile real hoy es el operario, que usa exclusivamente WhatsApp y no la UI web.
