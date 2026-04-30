"""Crea datos de demo para arrancar con el juego."""
from datetime import date, datetime, timedelta
from app.database import SessionLocal, Base, engine
from app import models
from app.security import hash_password

Base.metadata.create_all(bind=engine)


def run():
    db = SessionLocal()
    try:
        if db.query(models.User).count() > 0:
            print("Ya hay datos, skip seed.")
            return

        # Admin
        admin = models.User(
            name="Admin", last_name="Demo", email="admin@demo.com",
            phone="+5491100000001",
            password_hash=hash_password("demo1234"),
            role=models.UserRole.admin_finanzas,
            status=models.UserStatus.active,
            avatar="🧑‍💼", xp=120, onboarding_step=3,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        # Cuadrillas
        cuadrillas_data = [
            ("Los Maestros", "albañilería", "🧱", "#F59E0B", 8, 92.0, 3, 250),
            ("Volt Power", "electricidad", "⚡", "#FBBF24", 4, 88.0, 2, 180),
            ("Aqua Plomers", "plomería", "🚿", "#06B6D4", 3, 85.0, 2, 150),
            ("Color Squad", "pintura", "🎨", "#A855F7", 5, 78.0, 1, 80),
            ("Iron Crew", "herrería", "⚙️", "#94A3B8", 4, 90.0, 2, 200),
        ]
        cuadrillas = []
        for n, esp, av, col, miembros, ef, niv, exp in cuadrillas_data:
            c = models.Cuadrilla(
                nombre=n, especialidad=esp, avatar=av, color=col,
                cantidad_miembros=miembros, eficiencia=ef, nivel=niv,
                experiencia=exp, telefono="+541100000000",
            )
            db.add(c); cuadrillas.append(c)
        db.commit()

        # Proveedores
        proveedores_data = [
            ("Cementos Patagónicos", "30-12345-1", "+5491100000010", "ventas@cempat.com", "cemento", 4.5, 2),
            ("Hierros del Sur", "30-23456-2", "+5491100000011", "info@hierrossur.com", "hierro", 4.2, 4),
            ("Loma Negra Ladrillos", "30-34567-3", "+5491100000012", "ventas@loma.com", "ladrillos", 4.8, 1),
            ("Pinturas Pro", "30-45678-4", "+5491100000013", "ppro@gmail.com", "pinturas", 3.9, 5),
        ]
        proveedores = []
        for n, c, t, em, r, rt, pl in proveedores_data:
            p = models.Proveedor(nombre=n, cuit=c, telefono=t, email=em, rubro=r, rating=rt, plazo_entrega_dias=pl)
            db.add(p); proveedores.append(p)
        db.commit()

        # Materiales
        materiales_data = [
            ("Cemento Portland", "cemento", "bolsa", 240, 50, 8500, 0, "🟫"),
            ("Hierro 8mm", "hierro", "tn", 1.8, 0.5, 1850000, 1, "🔩"),
            ("Hierro 12mm", "hierro", "tn", 0.9, 0.5, 1900000, 1, "🔩"),
            ("Ladrillo común", "ladrillo", "u", 12500, 3000, 280, 2, "🧱"),
            ("Arena gruesa", "áridos", "m3", 18, 5, 12000, None, "🟨"),
            ("Piedra", "áridos", "m3", 12, 5, 14500, None, "⬛"),
            ("Cal hidráulica", "cemento", "bolsa", 35, 20, 6800, 0, "⬜"),
            ("Pintura látex", "terminaciones", "lata", 22, 10, 18000, 3, "🎨"),
            ("Cable 2.5mm", "instalaciones", "rollo", 14, 5, 32000, None, "🔌"),
            ("Caño PVC 110mm", "instalaciones", "u", 28, 10, 4500, None, "🔵"),
        ]
        for n, cat, u, st, mn, pr, pid, ic in materiales_data:
            m = models.Material(
                nombre=n, categoria=cat, unidad=u, stock=st, stock_minimo=mn,
                precio_unitario=pr,
                proveedor_id=proveedores[pid].id if pid is not None else None,
                icono=ic,
            )
            db.add(m)
        db.commit()

        # Obras
        obras_data = [
            ("Torre Aurora", "TA-2026-01", "Av. del Libertador 4500", "CABA",
             "Constructora del Sur SA", "Edificio residencial 18 pisos",
             "#3B82F6", "🏙️", models.ObraStatus.en_obra, 4500000, 2800000,
             date.today() - timedelta(days=120), date.today() + timedelta(days=180), 1200, 18),
            ("Country Las Lomas", "CL-2026-02", "Ruta 8 km 45", "Pilar",
             "Inmobiliaria Norte", "8 casas country", "#22C55E", "🏘️",
             models.ObraStatus.en_obra, 2800000, 1100000,
             date.today() - timedelta(days=60), date.today() + timedelta(days=240), 2400, 1),
            ("Galpón Industrial", "GI-2026-03", "Parque Industrial 12", "Tigre",
             "Logística Express", "Galpón 3000m2 con oficinas", "#F59E0B", "🏭",
             models.ObraStatus.en_obra, 1900000, 1200000,
             date.today() - timedelta(days=90), date.today() + timedelta(days=30), 3000, 2),
            ("Local Comercial Centro", "LC-2026-04", "San Martín 1234", "Vicente López",
             "Cliente Privado", "Refacción local 150m2", "#A855F7", "🏪",
             models.ObraStatus.planificacion, 380000, 0,
             date.today() + timedelta(days=15), date.today() + timedelta(days=90), 150, 1),
            ("Casa Quincho", "CQ-2026-05", "Av. Costanera 88", "San Isidro",
             "Familia Pérez", "Casa unifamiliar + quincho", "#EF4444", "🏡",
             models.ObraStatus.finalizada, 850000, 845000,
             date.today() - timedelta(days=240), date.today() - timedelta(days=10), 220, 2),
        ]
        obras = []
        for n, cd, dr, ci, cl, ds, co, ic, st, pt, pc, fi, ff, sup, pi in obras_data:
            o = models.Obra(
                nombre=n, codigo=cd, direccion=dr, ciudad=ci, cliente=cl,
                descripcion=ds, color=co, icono=ic, status=st,
                presupuesto_total=pt, presupuesto_consumido=pc,
                fecha_inicio=fi, fecha_fin_estimada=ff,
                superficie_m2=sup, pisos=pi,
            )
            db.add(o); obras.append(o)
        db.commit()

        # Frentes para cada obra
        frentes_torre = [
            ("Cimientos", "cimientos", "🧱", models.FrenteEstado.completado, 100, 0),
            ("Estructura piso 1-9", "estructura", "🏗️", models.FrenteEstado.completado, 100, 0),
            ("Estructura piso 10-18", "estructura", "🏗️", models.FrenteEstado.en_progreso, 65, 0),
            ("Mampostería", "mamposteria", "🧱", models.FrenteEstado.en_progreso, 40, 0),
            ("Instalaciones eléctricas", "instalaciones", "⚡", models.FrenteEstado.en_progreso, 30, 1),
            ("Instalaciones sanitarias", "instalaciones", "🚿", models.FrenteEstado.pendiente, 0, 2),
            ("Terminaciones", "terminaciones", "🎨", models.FrenteEstado.pendiente, 0, 3),
        ]
        frentes_country = [
            ("Movimiento de suelos", "cimientos", "🚜", models.FrenteEstado.completado, 100, 0),
            ("Cimientos lotes 1-4", "cimientos", "🧱", models.FrenteEstado.completado, 100, 0),
            ("Cimientos lotes 5-8", "cimientos", "🧱", models.FrenteEstado.en_progreso, 60, 0),
            ("Estructura lotes 1-4", "estructura", "🏗️", models.FrenteEstado.en_progreso, 35, 0),
            ("Mampostería lotes 1-4", "mamposteria", "🧱", models.FrenteEstado.pendiente, 0, None),
        ]
        frentes_galpon = [
            ("Cimientos", "cimientos", "🧱", models.FrenteEstado.completado, 100, 0),
            ("Estructura metálica", "estructura", "⚙️", models.FrenteEstado.completado, 100, 4),
            ("Cubierta", "estructura", "🏗️", models.FrenteEstado.en_progreso, 80, 4),
            ("Pisos industriales", "terminaciones", "⬜", models.FrenteEstado.en_progreso, 50, 0),
            ("Instalaciones", "instalaciones", "⚡", models.FrenteEstado.pendiente, 10, 1),
        ]
        for o, lst in [(obras[0], frentes_torre), (obras[1], frentes_country), (obras[2], frentes_galpon)]:
            for n, t, ic, est, prog, cidx in lst:
                cuad_id = cuadrillas[cidx].id if cidx is not None else None
                f = models.Frente(
                    obra_id=o.id, nombre=n, tipo=t, icono=ic,
                    estado=est, progreso=prog, cuadrilla_id=cuad_id,
                )
                db.add(f)
        db.commit()

        # Refrescar progreso de obras
        for o in obras[:3]:
            frentes = db.query(models.Frente).filter(models.Frente.obra_id == o.id).all()
            if frentes:
                o.progreso = sum(f.progreso for f in frentes) / len(frentes)
        db.commit()

        # Eventos varios
        eventos_data = [
            (obras[0].id, models.EventoTipo.material_llegada, "Llegada hormigón H21", "30m3 para piso 11", False),
            (obras[0].id, models.EventoTipo.avance, "Encofrado piso 11 listo", "Cuadrilla Los Maestros", False),
            (obras[0].id, models.EventoTipo.incidente, "Falta cemento crítico", "Stock bajo, urgente reponer", True),
            (obras[1].id, models.EventoTipo.hito, "Cimientos lote 4 completados", "Hito 25% obra", False),
            (obras[1].id, models.EventoTipo.foto, "Foto avance lotes 1-4", None, False),
            (obras[2].id, models.EventoTipo.inspeccion, "Inspección municipal", "Programada para viernes", False),
            (obras[2].id, models.EventoTipo.avance, "Cubierta 80%", "Faltan 20m2", False),
            (obras[0].id, models.EventoTipo.incidente, "Demora entrega hierro", "Proveedor avisó +3 días", True),
        ]
        for oid, t, tit, desc, cr in eventos_data:
            e = models.Evento(
                obra_id=oid, tipo=t, titulo=tit, descripcion=desc,
                es_critico=cr, canal=models.CanalCarga.whatsapp, usuario_id=admin.id,
            )
            db.add(e)
        db.commit()

        # Órdenes de trabajo
        ordenes_data = [
            (obras[0].id, "Hormigonar piso 11", "Espera hormigón H21 a las 9am", "alta", 0, 30),
            (obras[0].id, "Tirar cables piso 5", "Instalación eléctrica completa", "normal", 1, 20),
            (obras[1].id, "Encofrar lote 5", "Preparar para hormigonada", "normal", 0, 15),
            (obras[1].id, "Cargar camión áridos", "10m3 arena para cimientos", "baja", 0, 10),
            (obras[2].id, "Pintar paredes oficina", "Color blanco hueso", "baja", 3, 10),
            (obras[2].id, "Resolver gotera techo", "Filtración detectada en sector NE", "critica", 4, 50),
        ]
        for oid, t, d, p, cidx, xp in ordenes_data:
            ord_ = models.OrdenTrabajo(
                obra_id=oid, titulo=t, descripcion=d, prioridad=p,
                cuadrilla_id=cuadrillas[cidx].id, xp_reward=xp,
                creada_por_id=admin.id, canal_creacion=models.CanalCarga.web,
                fecha_limite=date.today() + timedelta(days=2),
            )
            db.add(ord_)
        db.commit()

        # Gastos
        gastos_data = [
            (obras[0].id, proveedores[0].id, "Materiales", 850000, "Cemento + cal mes 1"),
            (obras[0].id, proveedores[1].id, "Materiales", 1200000, "Hierro estructura"),
            (obras[0].id, None, "Mano de obra", 450000, "Cuadrilla Los Maestros 2 semanas"),
            (obras[0].id, None, "Servicios", 80000, "Alquiler grúa"),
            (obras[1].id, proveedores[2].id, "Materiales", 320000, "Ladrillos primer lote"),
            (obras[1].id, None, "Mano de obra", 280000, "Movimiento suelos"),
            (obras[2].id, proveedores[1].id, "Materiales", 680000, "Estructura metálica"),
            (obras[2].id, None, "Mano de obra", 320000, "Iron Crew estructura"),
        ]
        for oid, pid, cat, m, d in gastos_data:
            g = models.Gasto(
                obra_id=oid, proveedor_id=pid, categoria=cat, monto=m,
                descripcion=d, pagado=True, fecha=date.today() - timedelta(days=15),
            )
            db.add(g)
        db.commit()

        print("[OK] Seed completado!")
        print(f"   Login: admin@demo.com / demo1234")
        print(f"   {len(obras)} obras, {len(cuadrillas)} cuadrillas, {len(proveedores)} proveedores")
        print(f"   {len(materiales_data)} materiales, {len(eventos_data)} eventos, {len(ordenes_data)} órdenes")
    finally:
        db.close()


if __name__ == "__main__":
    run()
