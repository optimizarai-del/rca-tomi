# ⚡ Testing Checklist — Quick Reference

## 🚀 Iniciá aquí

```bash
# Terminal 1
python C:\Users\Usuario\Desktop\RCA\backend\run.py

# Terminal 2  
npm run dev   # desde C:\Users\Usuario\Desktop\RCA\frontend
```

Abra http://localhost:5173 → Login: `admin@demo.com` / `demo1234`

---

## 📋 Checklist por sección

### 1️⃣ OBRAS (WorldMap)
```
✓ Filtra entre estados (Todas | En obra | Planificación | Finalizadas)
✓ Grid responsive
✓ Click en obra → /obra-detail
```

### 2️⃣ OBRA DETAIL
```
✓ Hero title + ubicación + cliente
✓ Progress bar visual
✓ Crear frente → aparece en tabla
✓ Crear orden → aparece en lista
✓ Completar orden → aparece en Activity
✓ Botón atrás → vuelve a /world
```

### 3️⃣ ÓRDENES
```
✓ Lista global de órdenes
✓ Filtro por obra
✓ Resumen: pendientes | en_progreso | completadas
✓ Status badge correcto
```

### 4️⃣ CUADRILLAS
```
✓ Grid de equipos
✓ Crear cuadrilla: nombre + especialidad + cantidad
✓ Elimina con confirmación
✓ Persiste después de reload
```

### 5️⃣ MATERIALES
```
✓ Filtro por categoría
✓ Crear material: nombre + categoría + cantidad + unidad
✓ Editar cantidad
✓ Alerta si stock bajo (opcional)
```

### 6️⃣ PROVEEDORES
```
✓ Grid de proveedores
✓ Crear: nombre + especialidad + email + teléfono
✓ Editar datos
✓ Eliminar con confirmación
```

### 7️⃣ PRESUPUESTOS
```
✓ Muestra 3 big numbers (total, consumido, %)
✓ Gráficos cargan datos
✓ Cifras coherentes (suma manual)
```

### 8️⃣ USUARIOS
```
✓ Listar usuarios
✓ Invitar nuevo usuario (nombre + email + rol)
✓ Cambiar rol (select)
✓ Eliminar usuario
```

### 9️⃣ ACTIVIDAD (Feed)
```
✓ Lista cronológica eventos
✓ Eventos críticos en rojo
✓ Iconos correctos por tipo
✓ Timestamps correctos
```

### 🔟 NAVBAR (HUD)
```
✓ Logo clickeable → /world
✓ Stats compactos muestran datos reales
✓ Alerts si hay problemas
✓ Avatar + usuario
✓ Logout funciona
✓ Glass effect visible
```

### 1️⃣1️⃣ SIDEBAR
```
✓ Links activos = navy pill
✓ Hover effects suaves
✓ Eyebrows section labels
✓ Responsive (esconde en mobile)
```

---

## 🎨 Design QA

### Tipografía
```
✓ Hero titles: 5-6xl, bold, tracking-[-0.04em]
✓ Eyebrows: 12px, olive-700, uppercase, tracking-[0.22em]
✓ Body: Inter 400, text-navy
✓ Labels: 11px, uppercase
```

### Colores (Paleta RCA)
```
✓ Navy (#1E2B5E) — primary, backgrounds
✓ Olive (#8A9A5B) — accents, eyebrows
✓ Leather (#6B4C30) — warnings
✓ Bone (#EEEAE3) — surfaces, buttons secondary
✓ Tan (#C4B99A) — muted
```

### Espaciado
```
✓ Cards: rounded-3xl, p-6
✓ Buttons: rounded-full, px-5 py-2.5
✓ Inputs: rounded-2xl, px-4 py-3
✓ Hero headers: mb-12 (antes mb-10)
```

### Shadows
```
✓ soft: 1px 2px (hover subtle)
✓ card: 6px 24px (cards)
✓ lift: 8px 40px (modals)
```

---

## 🔗 Links directos

| Sección | URL |
|---------|-----|
| Login | http://localhost:5173/ |
| Obras | http://localhost:5173/world |
| Órdenes | http://localhost:5173/ordenes |
| Cuadrillas | http://localhost:5173/cuadrillas |
| Materiales | http://localhost:5173/materiales |
| Proveedores | http://localhost:5173/proveedores |
| Presupuestos | http://localhost:5173/finanzas |
| Usuarios | http://localhost:5173/equipo |
| Actividad | http://localhost:5173/feed |
| **API Docs** | **http://localhost:8000/docs** |

---

## 🧪 Flujo de testing rápido (5 min)

1. **Login** → `admin@demo.com` / `demo1234`
2. **Crear obra:**
   - Nombre: "Test Edificio"
   - Presupuesto: $100,000
3. **Crear frente en la obra:**
   - Nombre: "Cimientos"
4. **Crear orden:**
   - Descripción: "Excavar"
5. **Completar orden** → check status
6. **Ir a /feed** → debe aparecer evento
7. **Logout + Login** → datos persisten
✅ **PASS**: Todo funciona

---

## 🐛 Errores comunes

| Error | Solución |
|-------|----------|
| `Cannot GET /world` | Backend caído. Reinicia `python run.py` |
| CSS en rojo (Tailwind error) | Chequea opacidades: `/8` → `/10`, `/72` → `/70` |
| Datos no cargan | Recargá página (F5), backend tardó |
| Cards cuadradas | Vite no recompilió. Mata + `npm run dev` |
| Sidebar no aparece | Abrí console (F12), busca errores en Network |
| Login falla | Usa credenciales correctas: `admin@demo.com` / `demo1234` |

---

## 🎯 Performance goals

- Page load: < 1s
- Navigation: instant (Vite HMR)
- 100+ items: no lag
- Network requests: no 5xx errors
- Bundle size: < 500KB (gzip)

---

## 📸 Screenshots a validar

Toma screenshot de cada sección (F12 > Device Toggle) para:
- ✓ Desktop (1280px)
- ✓ Tablet (768px)
- ✓ Mobile (375px)

Verifica:
- Responsive layouts
- Touch targets ≥ 44px
- Text readable en todos tamaños
- No overflow horizontal

---

## 🚨 Critical paths (must work)

1. **Auth:** Login → Logout → Login newamente
2. **CRUD Obras:** Create → Read → Update → Delete
3. **CRUD Órdenes:** Create → Status change → Complete
4. **Real-time sync:** Edit en orden → aparece en feed inmediatamente
5. **Persistence:** Recargá página → datos siguen

---

## 📊 Test coverage target

| Área | Tests | Status |
|------|-------|--------|
| Authentication | 3 | ✓ Manual |
| CRUD Obras | 4 | ✓ Manual |
| CRUD Órdenes | 4 | ✓ Manual |
| CRUD Cuadrillas | 3 | ✓ Manual |
| CRUD Materiales | 3 | ✓ Manual |
| CRUD Proveedores | 3 | ✓ Manual |
| CRUD Usuarios | 3 | ✓ Manual |
| Dashboard HUD | 2 | ✓ Manual |
| Responsive | 3 | ✓ Manual |
| Design | 8 | ✓ Visual |
| **Total** | **41** | ✓ Ready |

---

Guardá esta checklist y usá mientras testeás. Marca items conforme los valides. ✅
