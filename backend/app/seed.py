"""Seed v0.4 — datos demo realistas alineados al modelo financiero del doc.

Carga:
- 3 regímenes fiscales estándar
- 1 super_admin
- 2 socios (User con rol admin para ser referenciables en aportes)
- 3 clientes (1 público RI, 1 privado RI, 1 particular)
- 2 obras: "IDS - Colegio Domingo Savio" (TOTAL_BLANCO) y "SP - San Pedro" (MIXTA)
- Etapas para cada obra
- Movimientos financieros de ejemplo (ingresos cliente, egresos MO/materiales/subcontrato, cheques, aportes)
- Capa lúdica mínima: 2 cuadrillas, materiales y proveedores demo
"""
from datetime import date, timedelta
from app.database import Base, engine, SessionLocal
from app import models
from app.security import hash_password


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(models.User).count() > 0:
            print("[seed] Ya hay datos. Si querés reiniciar, corré scripts/reset_db.py")
            return

        # ─── REGÍMENES FISCALES ───
        ri = models.RegimenFiscal(
            codigo="RI", nombre="Responsable Inscripto", iva_default=0.21,
            aplica_iibb=True, aplica_ganancias=True,
            descripcion="Responsable Inscripto en IVA — AFIP.",
        )
        mt = models.RegimenFiscal(
            codigo="MT", nombre="Monotributo", iva_default=0,
            aplica_iibb=True, aplica_ganancias=False,
            descripcion="Monotributista — sin IVA, paga IIBB en algunas jurisdicciones.",
        )
        ex = models.RegimenFiscal(
            codigo="EX", nombre="Exento / Consumidor Final", iva_default=0,
            aplica_iibb=False, aplica_ganancias=False,
            descripcion="Particular o entidad exenta.",
        )
        db.add_all([ri, mt, ex]); db.flush()

        # ─── USUARIOS ───
        admin = models.User(
            name="Admin", last_name="RCA", email="admin@rca.com",
            phone="+5491100000001", password_hash=hash_password("demo1234"),
            role=models.UserRole.super_admin, status=models.UserStatus.active,
            avatar="🛡️", xp=0,
        )
        socio_a = models.User(
            name="Socio", last_name="A", email="socio.a@rca.com",
            phone="+5491100000002", password_hash=hash_password("demo1234"),
            role=models.UserRole.admin_finanzas, status=models.UserStatus.active,
            avatar="👤", xp=0,
        )
        socio_b = models.User(
            name="Socio", last_name="B", email="socio.b@rca.com",
            phone="+5491100000003", password_hash=hash_password("demo1234"),
            role=models.UserRole.admin_finanzas, status=models.UserStatus.active,
            avatar="👤", xp=0,
        )
        capataz = models.User(
            name="Kevin", last_name="Rodriguez", email="kevin@rca.com",
            phone="+5491100000004", password_hash=hash_password("demo1234"),
            role=models.UserRole.supervisor, status=models.UserStatus.active,
            avatar="👷", xp=0,
        )
        db.add_all([admin, socio_a, socio_b, capataz]); db.flush()

        # ─── CLIENTES ───
        cli_publico = models.Cliente(
            nombre="Colegio Domingo Savio", tipo="publico",
            cuit="30-12345678-9", razon_social="Asociación Civil Domingo Savio",
            regimen_fiscal_id=ri.id, email="admin@savio.edu.ar",
            telefono="11-4444-5555", direccion="Av. Belgrano 1500, CABA",
        )
        cli_privado = models.Cliente(
            nombre="Constructora San Pedro SA", tipo="privado_ri",
            cuit="30-98765432-1", razon_social="Constructora San Pedro SA",
            regimen_fiscal_id=ri.id, email="contacto@sanpedro.com.ar",
        )
        cli_particular = models.Cliente(
            nombre="Familia García", tipo="particular",
            regimen_fiscal_id=ex.id,
        )
        db.add_all([cli_publico, cli_privado, cli_particular]); db.flush()

        # ─── OBRAS ───
        today = date.today()
        ids_obra = models.Obra(
            codigo="IDS", nombre="IDS — Colegio Domingo Savio Patio + Baños",
            cliente_id=cli_publico.id, regimen_fiscal_id=ri.id,
            tipo_facturacion=models.TipoFacturacion.TOTAL_BLANCO,
            direccion="Av. Belgrano 1500", ciudad="CABA",
            descripcion="Refacción de patio cubierto y baños del colegio Domingo Savio.",
            monto_contrato=12_500_000,
            fecha_inicio=today - timedelta(days=45),
            fecha_fin_estimada=today + timedelta(days=90),
            estado=models.ObraStatus.EN_CURSO,
            icono="🏫", color="#1E2B5E",
            superficie_m2=350, pisos=1,
        )
        sp_obra = models.Obra(
            codigo="SP", nombre="SP — Casa San Pedro",
            cliente_id=cli_privado.id, regimen_fiscal_id=ri.id,
            tipo_facturacion=models.TipoFacturacion.MIXTA,
            direccion="Calle 12 nro 450", ciudad="San Pedro, BA",
            descripcion="Construcción de casa de fin de semana, 180 m².",
            monto_contrato=8_200_000,
            fecha_inicio=today - timedelta(days=20),
            fecha_fin_estimada=today + timedelta(days=120),
            estado=models.ObraStatus.EN_CURSO,
            icono="🏡", color="#3D4F1E",
            superficie_m2=180, pisos=1,
        )
        db.add_all([ids_obra, sp_obra]); db.flush()

        # ─── ETAPAS ───
        ids_etapas = [
            models.EtapaObra(obra_id=ids_obra.id, nombre="Anticipo", nro_etapa=0,
                             monto_contractual=2_500_000, porcentaje_avance=20,
                             estado=models.EtapaEstado.COBRADA,
                             fecha_estimada=today - timedelta(days=40),
                             fecha_cobro_real=today - timedelta(days=38),
                             notas="Cobrado contra firma de contrato."),
            models.EtapaObra(obra_id=ids_obra.id, nombre="Etapa 1 — Demolición y cimientos", nro_etapa=1,
                             monto_contractual=4_000_000, porcentaje_avance=35,
                             estado=models.EtapaEstado.EJECUTADA,
                             fecha_estimada=today + timedelta(days=10),
                             notas="Esperando certificación municipal."),
            models.EtapaObra(obra_id=ids_obra.id, nombre="Etapa 2 — Terminaciones", nro_etapa=2,
                             monto_contractual=4_500_000, porcentaje_avance=35,
                             estado=models.EtapaEstado.PENDIENTE,
                             fecha_estimada=today + timedelta(days=60)),
            models.EtapaObra(obra_id=ids_obra.id, nombre="Final de obra", nro_etapa=3,
                             monto_contractual=1_500_000, porcentaje_avance=10,
                             estado=models.EtapaEstado.PENDIENTE,
                             fecha_estimada=today + timedelta(days=90)),
        ]
        sp_etapas = [
            models.EtapaObra(obra_id=sp_obra.id, nombre="Anticipo", nro_etapa=0,
                             monto_contractual=2_000_000, porcentaje_avance=25,
                             estado=models.EtapaEstado.COBRADA,
                             fecha_cobro_real=today - timedelta(days=18)),
            models.EtapaObra(obra_id=sp_obra.id, nombre="Etapa 1 — Estructura", nro_etapa=1,
                             monto_contractual=3_500_000, porcentaje_avance=45,
                             estado=models.EtapaEstado.EN_EJECUCION,
                             fecha_estimada=today + timedelta(days=30)),
            models.EtapaObra(obra_id=sp_obra.id, nombre="Final de obra", nro_etapa=2,
                             monto_contractual=2_700_000, porcentaje_avance=30,
                             estado=models.EtapaEstado.PENDIENTE,
                             fecha_estimada=today + timedelta(days=110)),
        ]
        db.add_all(ids_etapas + sp_etapas); db.flush()

        # ─── MOVIMIENTOS — IDS ───
        db.add(models.MovimientoObra(
            obra_id=ids_obra.id, etapa_id=ids_etapas[0].id,
            fecha=today - timedelta(days=38),
            tipo=models.TipoMovimiento.INGRESO,
            origen_ingreso=models.OrigenIngreso.ANTICIPO_CLIENTE,
            concepto="Anticipo Colegio Domingo Savio — Etapa 0",
            monto=2_500_000, medio_pago=models.MedioPago.TRANSFERENCIA,
            estado=models.EstadoMovimiento.CONFIRMADO,
            hoja_fisica=f"Hoja 1 - {(today - timedelta(days=38)).isoformat()}",
            cargado_por=admin.id,
        ))
        for i, w in enumerate([35, 28, 21, 14, 7]):
            db.add(models.MovimientoObra(
                obra_id=ids_obra.id, etapa_id=ids_etapas[1].id,
                fecha=today - timedelta(days=w),
                tipo=models.TipoMovimiento.EGRESO,
                categoria_egreso=models.CategoriaEgreso.MANO_DE_OBRA,
                concepto=f"Kevin Rodriguez — MO semana {i+1}",
                monto=320_000, medio_pago=models.MedioPago.EFECTIVO,
                estado=models.EstadoMovimiento.CONFIRMADO,
                hoja_fisica=f"Hoja {i+2} - {(today - timedelta(days=w)).isoformat()}",
                cargado_por=admin.id,
            ))
        comp_holcim = models.Comprobante(
            obra_id=ids_obra.id,
            tipo_comprobante=models.TipoComprobante.FC_A,
            punto_venta=1, nro_comprobante="00001-00012345",
            fecha_emision=today - timedelta(days=20),
            cuit_emisor="30-50001234-5", cuit_receptor="30-50009999-9",
            neto_gravado=380_000, neto_no_gravado=0, iva_21=79_800, iva_105=0,
            total=459_800, cae="74123456789012",
            cae_vencimiento=today + timedelta(days=10),
            es_venta=False, estado_fiscal=models.EstadoFiscal.VALIDO,
        )
        db.add(comp_holcim); db.flush()
        db.add(models.MovimientoObra(
            obra_id=ids_obra.id, etapa_id=ids_etapas[1].id,
            fecha=today - timedelta(days=20),
            tipo=models.TipoMovimiento.EGRESO,
            categoria_egreso=models.CategoriaEgreso.MATERIALES,
            concepto="Hormigón Holcim — 30m³",
            monto=459_800, medio_pago=models.MedioPago.TRANSFERENCIA,
            comprobante_id=comp_holcim.id,
            estado=models.EstadoMovimiento.CONFIRMADO,
            hoja_fisica=f"Hoja 7 - {(today - timedelta(days=20)).isoformat()}",
            cargado_por=admin.id,
        ))
        db.add(models.MovimientoObra(
            obra_id=ids_obra.id, etapa_id=ids_etapas[1].id,
            fecha=today - timedelta(days=5),
            tipo=models.TipoMovimiento.EGRESO,
            categoria_egreso=models.CategoriaEgreso.SUBCONTRATO,
            concepto="Subcontrato instalación eléctrica",
            monto=850_000, medio_pago=models.MedioPago.CHEQUE_PROPIO,
            nro_cheque="00045123", banco="Banco Galicia",
            fecha_vto_cheque=today + timedelta(days=15),
            estado=models.EstadoMovimiento.A_REVISAR,
            hoja_fisica=f"Hoja 8 - {(today - timedelta(days=5)).isoformat()}",
            cargado_por=admin.id,
        ))

        # ─── APORTE EN SP + INGRESO ESPEJO ───
        aporte = models.AporteSocio(
            obra_id=sp_obra.id, socio_id=socio_a.id,
            etapa_reintegro_id=sp_etapas[1].id,
            fecha_aporte=today - timedelta(days=10),
            monto=600_000,
            motivo="Cubre déficit semana 09 — pago albañiles San Pedro",
            medio_pago=models.MedioPago.TRANSFERENCIA,
            estado_devolucion=models.EstadoDevolucion.PENDIENTE,
            monto_devuelto=0,
        )
        db.add(aporte); db.flush()
        db.add(models.MovimientoObra(
            obra_id=sp_obra.id, etapa_id=sp_etapas[1].id,
            fecha=aporte.fecha_aporte,
            tipo=models.TipoMovimiento.INGRESO,
            origen_ingreso=models.OrigenIngreso.APORTE_SOCIO_RCA,
            concepto=f"Aporte de socio: {aporte.motivo}",
            monto=aporte.monto, medio_pago=aporte.medio_pago,
            aporte_socio_id=aporte.id,
            estado=models.EstadoMovimiento.CONFIRMADO,
            canal=models.CanalCarga.automatico,
            cargado_por=admin.id,
        ))

        # SP movimientos
        db.add(models.MovimientoObra(
            obra_id=sp_obra.id, etapa_id=sp_etapas[0].id,
            fecha=today - timedelta(days=18),
            tipo=models.TipoMovimiento.INGRESO,
            origen_ingreso=models.OrigenIngreso.ANTICIPO_CLIENTE,
            concepto="Anticipo San Pedro",
            monto=2_000_000, medio_pago=models.MedioPago.TRANSFERENCIA,
            cargado_por=admin.id,
        ))
        db.add(models.MovimientoObra(
            obra_id=sp_obra.id, etapa_id=sp_etapas[1].id,
            fecha=today - timedelta(days=8),
            tipo=models.TipoMovimiento.EGRESO,
            categoria_egreso=models.CategoriaEgreso.MATERIALES,
            concepto="Ladrillos 5000 unidades",
            monto=380_000, medio_pago=models.MedioPago.EFECTIVO,
            estado=models.EstadoMovimiento.CONFIRMADO,
            hoja_fisica=f"SP-Hoja 3 - {(today - timedelta(days=8)).isoformat()}",
            cargado_por=admin.id,
        ))
        db.add(models.MovimientoObra(
            obra_id=sp_obra.id, etapa_id=sp_etapas[1].id,
            fecha=today - timedelta(days=3),
            tipo=models.TipoMovimiento.EGRESO,
            categoria_egreso=models.CategoriaEgreso.MANO_DE_OBRA,
            concepto="Albañiles San Pedro — semana",
            monto=480_000, medio_pago=models.MedioPago.EFECTIVO,
            estado=models.EstadoMovimiento.CONFIRMADO,
            cargado_por=admin.id,
        ))

        # ─── CAPA LÚDICA / OPERATIVA ───
        cuad_a = models.Cuadrilla(
            nombre="Los Maestros", especialidad="albañilería", avatar="🧱",
            cantidad_miembros=4, nivel=3, experiencia=850, eficiencia=88,
            capataz_id=capataz.id, telefono="+5491100000004",
        )
        cuad_b = models.Cuadrilla(
            nombre="Volt Power", especialidad="electricidad", avatar="⚡",
            cantidad_miembros=2, nivel=2, experiencia=420, eficiencia=92,
        )
        db.add_all([cuad_a, cuad_b]); db.flush()
        db.add_all([
            models.Frente(obra_id=ids_obra.id, nombre="Cimientos", tipo="cimientos",
                          icono="🟫", estado=models.FrenteEstado.completado,
                          progreso=100, cuadrilla_id=cuad_a.id),
            models.Frente(obra_id=ids_obra.id, nombre="Mampostería", tipo="mamposteria",
                          icono="🧱", estado=models.FrenteEstado.en_progreso,
                          progreso=60, cuadrilla_id=cuad_a.id),
            models.Frente(obra_id=ids_obra.id, nombre="Instalaciones eléctricas", tipo="instalaciones",
                          icono="⚡", estado=models.FrenteEstado.pendiente,
                          progreso=10, cuadrilla_id=cuad_b.id),
            models.Frente(obra_id=sp_obra.id, nombre="Estructura", tipo="estructura",
                          icono="⬛", estado=models.FrenteEstado.en_progreso,
                          progreso=40, cuadrilla_id=cuad_a.id),
        ])
        db.add_all([
            models.Proveedor(nombre="Holcim", cuit="30-50001234-5", rubro="cemento",
                             rating=4.7, plazo_entrega_dias=2, telefono="11-4555-1111"),
            models.Proveedor(nombre="Acindar", cuit="30-50001235-6", rubro="hierro",
                             rating=4.5, plazo_entrega_dias=4),
            models.Proveedor(nombre="Pinturería Argento", rubro="pinturas",
                             rating=4.2, plazo_entrega_dias=3),
            models.Proveedor(nombre="Eléctrica Sur", rubro="electricidad",
                             rating=4.0, plazo_entrega_dias=5, moroso=True),
        ])
        db.add_all([
            models.Material(nombre="Cemento Holcim", categoria="cemento", unidad="bolsa",
                            stock=120, stock_minimo=50, precio_unitario=8500, icono="🧱"),
            models.Material(nombre="Hierro 8mm", categoria="hierro", unidad="barra",
                            stock=18, stock_minimo=30, precio_unitario=12000, icono="🔩"),
            models.Material(nombre="Ladrillos comunes", categoria="ladrillo", unidad="u",
                            stock=4500, stock_minimo=1000, precio_unitario=180, icono="🧱"),
            models.Material(nombre="Pintura látex 20L", categoria="terminaciones", unidad="balde",
                            stock=4, stock_minimo=10, precio_unitario=85000, icono="🎨"),
        ])
        db.add_all([
            models.Evento(obra_id=ids_obra.id, tipo=models.EventoTipo.material_llegada,
                          titulo="Llegó hormigón Holcim", descripcion="30m³ recibidos en obra.",
                          es_critico=False, usuario_id=capataz.id),
            models.Evento(obra_id=ids_obra.id, tipo=models.EventoTipo.incidente,
                          titulo="Demora en certificación municipal",
                          descripcion="Esperando inspección desde hace 5 días.",
                          es_critico=True, usuario_id=admin.id),
            models.Evento(obra_id=sp_obra.id, tipo=models.EventoTipo.avance,
                          titulo="Estructura al 40%", es_critico=False, usuario_id=capataz.id),
        ])

        db.commit()
        print("[seed] OK — datos demo cargados.")
        print(f"   Login: admin@rca.com / demo1234")
        print(f"   2 obras (IDS, SP), 7 etapas, 13+ movimientos, 1 aporte de socio.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
