# 📚 Sprints — historia del proyecto

Cada sprint corresponde a un commit en `git log` y se documenta acá con el mismo formato:
**Requisitos** (qué problema resolvió), **Cómo se hizo** (implementación), **Cómo se usa** (instrucciones para alguien externo), **Tests** (qué se validó) y **Estado** (qué quedó pendiente).

| # | Sprint | Estado | Documento |
|---|---|---|---|
| 0 | Setup inicial — scripts y onboarding | ✅ | [SPRINT_0_setup.md](SPRINT_0_setup.md) |
| 1 | Operario IA de solo lectura | ✅ | [SPRINT_1_agente_lectura.md](SPRINT_1_agente_lectura.md) |
| A+B | Modelo financiero RCA (clientes, etapas, movimientos, R1–R5) | ✅ | [SPRINT_AB_modelo_financiero.md](SPRINT_AB_modelo_financiero.md) |
| 2 | Agente IA con escritura + confirmación humana | ✅ (T6/T13 bloqueados sin saldo Anthropic) | [SPRINT_2_agente_escritura.md](SPRINT_2_agente_escritura.md) |
| 3 | UI completa de gestión financiera | ✅ | [SPRINT_3_ui_finanzas.md](SPRINT_3_ui_finanzas.md) |
| 4 | WhatsApp bidireccional + magic links | ✅ | [SPRINT_4_whatsapp.md](SPRINT_4_whatsapp.md) |
| 7 | Roles y permisos + tabla Socio propia | ✅ (suite 49/49) | [SPRINT_7_roles.md](SPRINT_7_roles.md) |
| 8 | Producción: Alembic + pytest + CI + Docker + Sentry + backups | ✅ (deploy real requiere acciones del usuario) | [SPRINT_8_produccion.md](SPRINT_8_produccion.md) |
| 9 | Stock multi-ubicación (depósito · en obras · pendiente retiro) | ✅ (suite 77/77) | [SPRINT_9_stock_multiubicacion.md](SPRINT_9_stock_multiubicacion.md) |
| 10 | Presupuestos de materiales por obra | ✅ (suite 77/77) | [SPRINT_10_presupuestos_materiales.md](SPRINT_10_presupuestos_materiales.md) |
| 11 | Bot de Telegram (texto) + vinculación de usuarios | ✅ (suite 90/90) | [SPRINT_11_telegram_bot.md](SPRINT_11_telegram_bot.md) |
| 13 | UI cleanup + permisos granulares (secciones + obras) | ✅ (suite 103/103) | [SPRINT_13_ui_permisos.md](SPRINT_13_ui_permisos.md) |
| 14 | Stock: estados pedido/retirar/retirado + alertas + foto factura | ✅ (suite 133/133) | [SPRINT_14_stock_retiros.md](SPRINT_14_stock_retiros.md) |
| 17 | Requerimientos por obra (bot + web) | ✅ (suite 115/115) | [SPRINT_17_requerimientos.md](SPRINT_17_requerimientos.md) |
| 12 | Perfil demo dual (`is_demo` + scoping automático) | ✅ | — |
| 20 | Deploy producción + dominio + handoff a Tomi | 🟡 en curso | [SPRINT_20_deploy_handoff.md](SPRINT_20_deploy_handoff.md) |


## Cómo seguir leyendo

- Para entender **el panorama actual del proyecto**, leer primero [../GUIA_PROYECTO.md](../GUIA_PROYECTO.md).
- Para ver **qué viene después**, leer [../PLAN_SPRINTS_13_20.md](../PLAN_SPRINTS_13_20.md) (vigente).
- Para correrlo en una PC nueva, [../../SETUP.md](../../SETUP.md).

## Convenciones de los documentos

- Las rutas a archivos del repo van con path absoluto desde la raíz: `backend/app/models.py`, `frontend/src/pages/Movimientos.jsx`.
- Los endpoints van con verbo + path: `POST /api/movimientos`.
- Los comandos asumen que estás parado en la raíz del repo.
- Los identificadores entre paréntesis (T1, T2…) son las tareas del sprint según [../PLAN_ACCION.md](../PLAN_ACCION.md).
