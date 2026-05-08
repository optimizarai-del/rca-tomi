# 📋 Guía de Onboarding — RCA Platform

## Introducción
RCA es una plataforma minimalista (estilo Apple) para gestionar **obras de construcción, equipos, materiales, proveedores y presupuestos** en tiempo real.

**URLs:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Docs API: http://localhost:8000/docs

---

## 🚀 Paso 0: Iniciar los servidores

### Opción A: Archivos batch (Windows)
1. Abre el explorador en `C:\Users\Usuario\Desktop\RCA`
2. Doble-clic en `start-backend.bat` → se abre consola con FastAPI en puerto 8000
3. Doble-clic en `start-frontend.bat` → se abre consola con Vite en puerto 5173
4. Espera 10-15 segundos a que ambos carguen

### Opción B: Terminal manual
```bash
# Terminal 1 — Backend
cd C:\Users\Usuario\Desktop\RCA\backend
python run.py

# Terminal 2 — Frontend
cd C:\Users\Usuario\Desktop\RCA\frontend
npm run dev
```

✅ Ambos servidores corriendo cuando ves:
- Backend: `Uvicorn running on http://0.0.0.0:8000`
- Frontend: `Local: http://localhost:5173`

---

## 🔐 Paso 1: Login

### Credenciales de demo
**Email:** `admin@demo.com`
**Contraseña:** `demo1234`

1. Abrí http://localhost:5173
2. Verás login con diseño Apple — hero bicolor (navy + olive)
3. Los campos están pre-llenados — solo clickeá **"Continuar"**
4. Serás redirigido a `/world` (Obras)

**Acceso:** Admin full (máximo nivel de permisos)

---

## 🏗️ Paso 2: Dashboard principal — Obras (WorldMap)

### Qué ves
- **Hero title:** "Tus obras en un solo lugar"
- **Filtros:** Todas | En obra | Planificación | Finalizadas
- **Grid de obras:** Cards con cada proyecto

### Testea esto
- [ ] Filtrá entre estados (deberían cambiar los conteos)
- [ ] Clickeá una obra → detalle completo
- [ ] Verificá que la UI sea responsive (achicá navegador)

---

## 🏢 Paso 3: Detalle de Obra (ObraDetail)

### Layout de ObraDetail
Entrás por cualquier obra del grid. Verás:

#### Sección 1: Encabezado
- **Código + Estado:** Chip con status (en_obra | planificacion | finalizada)
- **Título:** Nombre de la obra (6xl keynote style)
- **Ubicación + Cliente:** Subtítulos con iconos
- **Health indicator:** Bolita de color (verde=bien, amarillo=medio, rojo=crítico)
- **Progress bar:** Avance visual 0-100%

#### Sección 2: Frentes de trabajo
- Card con tabla de frentes activos
- Botón **"Nuevo frente"** (abre modal)
- Testea: Crear 1 frente, editar, eliminar

#### Sección 3: Órdenes de trabajo
- Lista de órdenes por estado
- Botón **"Nueva orden"**
- Testea: Crear orden, cambiar status (pendiente → en_progreso → completada)

#### Sección 4: Actividad (Feed)
- Cronología de cambios en la obra
- Automática — se actualiza al crear frentes/órdenes

### Testea todo esto
```
✓ Entra a obra "Edificio Central"
✓ Crea 1 frente: Nombre=Cimientos, Especialidad=Excavación
✓ Crea 1 orden de trabajo: Descripción="Excavar 50m³"
✓ Completa la orden → debe aparecer en activity
✓ Vuelve atrás (botón "Obras")
```

---

## 📊 Paso 4: Órdenes (Vista global)

**Ruta:** Sidebar izq → "Órdenes" o http://localhost:5173/ordenes

### Qué ves
- Hero: "Órdenes. Tareas activas en todas tus obras"
- Filtro por obra (dropdown)
- Card grande con resumen (pendientes | en progreso | completadas)
- Tabla completa abajo

### Testea
```
✓ Filtrá por una obra específica
✓ Verifica que aparezcan las órdenes que creaste
✓ Clickeá una orden → debe abrir detalle (si existe ruta)
✓ Cambiar estado desde aquí (si hay controles)
```

---

## 👥 Paso 5: Cuadrillas (Equipos)

**Ruta:** Sidebar → "Cuadrillas" o http://localhost:5173/cuadrillas

### Qué ves
- Hero: "Cuadrillas. Equipos de trabajo..."
- Botón **"Nueva cuadrilla"** (arriba)
- Grid de cards por cuadrilla

### Cards de cuadrilla muestran
- Nombre de cuadrilla
- Especialidad (excavación, albañilería, pintura, etc)
- Cantidad de miembros
- Botón eliminar (trash icon)

### Testea
```
✓ Crea cuadrilla: 
  - Nombre: "Equipo Excavación"
  - Especialidad: "Excavación"
  - Cantidad miembros: 5
✓ Verifica que aparezca en el grid
✓ Intenta eliminar (debe pedir confirmación)
✓ Recarga la página (debe persistir en BD)
```

---

## 📦 Paso 6: Materiales (Inventario)

**Ruta:** Sidebar → "Materiales" o http://localhost:5173/materiales

### Qué ves
- Hero: "Materiales. Stock organizado..."
- Filtros por categoría (botones pill)
- Grid organizado por categoría

### Testea
```
✓ Filtrá por categoría (Todos | Acero | Concreto | Madera)
✓ Crea material nuevo:
  - Nombre: "Hormigón 3000 PSI"
  - Categoría: "Concreto"
  - Cantidad: 100 m³
  - Unidad: m³
✓ Edita cantidad (debe decrecer/crecer)
✓ Verifica alertas inteligentes si stock bajo
```

---

## 🚚 Paso 7: Proveedores (Red de aliados)

**Ruta:** Sidebar → "Proveedores" o http://localhost:5173/proveedores

### Qué ves
- Hero: "Proveedores. Tu red de confianza..."
- Grid de cards (nombre, especialidad, contacto)
- Botón **"Nuevo proveedor"**

### Testea
```
✓ Crea proveedor:
  - Nombre: "Constructora XYZ S.A."
  - Especialidad: "Hormigón"
  - Email: contact@xyz.com
  - Teléfono: +5491234567890
✓ Edita proveedor
✓ Elimina con confirmación
```

---

## 💰 Paso 8: Presupuestos (Finanzas)

**Ruta:** Sidebar → "Presupuestos" o http://localhost:5173/finanzas

### Qué ves
- Hero: "Presupuestos. Control completo..."
- **3 big numbers (Apple keynote style):**
  - Total comprometido (suma de todos los presupuestos)
  - Consumido (gasto real)
  - % utilización
- **2 gráficos:**
  - Por categoría (horizontal bar chart)
  - Por obra (breakdown)

### Testea
```
✓ Verifica que los números sean coherentes
✓ Suma manual: si hay 2 obras de $10k cada = $20k total
✓ Visualiza los gráficos (deben cargar datos)
✓ Si no hay datos, crea 2 obras con presupuestos
```

---

## 👤 Paso 9: Usuarios (Administración)

**Ruta:** Sidebar → "Usuarios" o http://localhost:5173/equipo

**Nota:** Solo visible si sos admin

### Qué ves
- Hero: "Usuarios. Gestión de accesos..."
- Tabla con usuarios del sistema
- Botón **"Invitar usuario"**
- Select por usuario para cambiar rol

### Roles disponibles
- `admin` — acceso total
- `jefe_obra` — solo sus obras
- `admin_finanzas` — finanzas + obras
- `obrero` — solo órdenes asignadas

### Testea
```
✓ Invita usuario:
  - Nombre: "Juan Pérez"
  - Email: juan@obra.com
  - Rol: "jefe_obra"
✓ Cambiar rol de usuario existente (select)
✓ Si es posible, borra usuario (Trash icon)
```

---

## 📢 Paso 10: Actividad (Feed)

**Ruta:** Sidebar → "Actividad" o http://localhost:5173/feed

### Qué ves
- Hero: "Actividad. Cronología de todo..."
- Lista ordenada cronológicamente (más reciente arriba)
- Eventos con iconos (◆ avance, ◇ material, ! incidente, ★ hito, etc)

### Tipos de evento
- `avance` — cambio en progreso
- `material_llegada` — stock llegó
- `incidente` — alerta roja
- `inspeccion` — check
- `foto` — evidencia fotográfica
- `hito` — milestone
- `otro` — genérico

### Eventos críticos
- Si `es_critico=true` → chip rojo, icono warning

### Testea
```
✓ Crea acciones en otras secciones (órdenes, frentes, etc)
✓ Vuelve a Feed
✓ Deberías ver los eventos ahí (actividad en vivo)
✓ Verifica que timestamp sea correcto
✓ Filtra por obra si hay opción
```

---

## 🎨 Paso 11: Verifica el diseño Apple

### Elementos clave a chequear

#### Top Nav (Header HUD)
- [ ] Barra fina (48px) con glass effect
- [ ] Logo RCA clickeable (vuelve a /world)
- [ ] Stats compactos: Disponible | Obras | Equipo | Productividad
- [ ] Alerts si hay problemas
- [ ] Avatar + logout a la derecha
- [ ] Hover effects suaves

#### Sidebar
- [ ] Rounded pills activas (navy filled)
- [ ] Transiciones smooth
- [ ] Secciones con eyebrow uppercase
- [ ] Footer con versión + tagline

#### Páginas (Hero headers)
- [ ] Eyebrow uppercase olive (ej: "Recursos humanos")
- [ ] Título 5-6xl bold con tracking tight
- [ ] Subtítulo light gris (hero-sub)
- [ ] Punto al final del título (ej: "Cuadrillas.")

#### Cards
- [ ] `rounded-3xl` (generoso radio)
- [ ] Border suave
- [ ] Hover effect: subir + shadow
- [ ] Espaciado interno 6 (p-6)

#### Inputs
- [ ] `rounded-2xl` (más que buttons)
- [ ] Focus ring navy/10
- [ ] Placeholder muted
- [ ] Smooth transitions

#### Buttons
- [ ] Pill shape `rounded-full`
- [ ] Navy primary, Bone secondary
- [ ] Active: `scale-[0.97]`
- [ ] Tracking tight

---

## 🔧 Paso 12: API directo (testing avanzado)

**URL:** http://localhost:8000/docs

Verás SwaggerUI interactivo — testea endpoints:

### Endpoints principales

#### Obras
```
GET   /api/obras           → Listar todas
POST  /api/obras           → Crear
GET   /api/obras/{id}      → Detalle
PUT   /api/obras/{id}      → Editar
```

#### Órdenes
```
GET   /api/ordenes         → Listar todas
POST  /api/ordenes         → Crear
```

#### Cuadrillas
```
GET   /api/cuadrillas      → Listar
POST  /api/cuadrillas      → Crear
```

#### Eventos (Activity)
```
GET   /api/eventos/?limit=50  → Últimos 50 eventos
POST  /api/eventos            → Crear evento manual
```

#### Dashboard HUD
```
GET   /api/dashboard/hud   → Stats resumen
```

### Testea en Swagger
1. Abrí http://localhost:8000/docs
2. Expandí un endpoint (ej: `GET /api/obras`)
3. Clickeá **"Try it out"**
4. Clickeá **"Execute"**
5. Verás request + response real

---

## ✅ Checklist de testing completo

### Frontend
- [ ] Login/logout funcionan
- [ ] Sidebar navega entre páginas
- [ ] Top-nav es sticky + muestra stats
- [ ] Responsive: mobile, tablet, desktop
- [ ] Dark mode (si aplica)
- [ ] Hover effects suaves
- [ ] Focus rings accesibles
- [ ] Transiciones con HMR en Vite

### Funcionalidad CRUD
- [ ] **Obras:** crear, editar, listar, ver detalle
- [ ] **Órdenes:** crear, cambiar status, completar
- [ ] **Cuadrillas:** crear, editar, eliminar
- [ ] **Materiales:** crear, editar cantidad
- [ ] **Proveedores:** crear, contactar, eliminar
- [ ] **Usuarios:** invitar, cambiar rol
- [ ] **Frentes:** crear en obra, listar, eliminar

### Data persistence
- [ ] Recargá página → datos persisten
- [ ] Crea en /ordenes → aparece en /feed automáticamente
- [ ] Presupuesto se suma en /finanzas
- [ ] Equipo suma en /dashboard/hud

### Design & UX
- [ ] Paleta RCA (navy, olive, leather, tan, bone)
- [ ] Typography SF Pro / Inter coherente
- [ ] Cards rounded-3xl sin borders duros
- [ ] Buttons pill con tracking-tight
- [ ] Hero titles 5-6xl con punto
- [ ] Eyebrows olive-700 uppercase
- [ ] Shadows soft, card, lift coherentes

### Performance
- [ ] Páginas cargan < 1s
- [ ] Listados con 100+ items no lagguean
- [ ] Vite HMR funciona (guardás, actualiza)
- [ ] Network tab sin errores 5xx

---

## 🐛 Troubleshooting

### "Cannot GET /world" o error 404
→ Backend no responde. Recargá backend: `python run.py`

### Estilos no aplican (CSS in red)
→ Error Tailwind. Chequea `/8` o `/72` en index.css (inválidos)
→ Tailwind solo acepta `/5 /10 /15 .../95`

### Login falla "Invalid credentials"
→ Demo es `admin@demo.com` / `demo1234`
→ Checkea que backend esté corriendo

### "TypeError: Cannot read property..." en console
→ Data no cargó. Backend tardó. Recargá página.

### Cards se ven cuadradas, no rounded
→ Vite no recompilió. Mata frontend + `npm run dev` nuevamente

### Sidebar no aparece
→ Layout.jsx renderiza mal. Checkea console (Network > /api/*)

---

## 📝 Datos de prueba recomendados

### Obras para crear
```
1. Edificio Central — Rosario
   - Presupuesto: $500,000
   - Avance: 45%
   
2. Puente Nuevo — San Nicolás
   - Presupuesto: $1,200,000
   - Avance: 20%
```

### Cuadrillas
```
- Equipo Excavación (5 personas)
- Equipo Albañilería (8 personas)
- Equipo Acabados (4 personas)
```

### Materiales
```
- Hormigón 3000 PSI (100 m³)
- Acero 1/2" (50 ton)
- Ladrillos comunes (10,000 un)
- Pintura vinílica (100 latas)
```

### Proveedores
```
- Constructora XYZ (Hormigón)
- Acería Argentina (Acero)
- Ladrillería Santa Fe (Ladrillos)
```

---

## 🎯 Flujo ideal de testing (15 minutos)

```
1. [2 min] Login → Dashboard (/world)
2. [3 min] Crear 1 obra + 2 frentes + 1 orden
3. [2 min] Completar orden → ver en /feed
4. [2 min] Crear cuadrilla + material
5. [2 min] Navega /finanzas, /ordenes, /actividad
6. [2 min] Logout + login nuevamente
✓ Done! Todo funciona.
```

---

## 📞 Soporte

Si algo no funciona:
1. Abrí console (F12) → Network tab
2. Filtrá por `/api/` → checkea status de requests
3. Swagger: http://localhost:8000/docs → testea endpoint directo
4. Backend log: busca `error` o `exception`

**Usuarios demo adicionales** (si creastes):
- Necesitás invitar desde /equipo
- O editar `backend/app/models.py` + `seed_data.py`

---

¡Listo! Segí paso a paso y probá todo 🚀
