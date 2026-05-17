"""Modelo de datos RCA. — Sistema de gestión de costos y flujo de caja por obra.

Sigue el spec del documento "Modelo de gestión de gastos de obra v1.0 — Mayo 2026".
Decisiones de implementación:
- Integer PKs (en vez de UUID del doc) por simplicidad y consistencia con código previo.
- SQLAlchemy + eventos en vez de triggers PG (portable a SQLite).
- Capa lúdica (Cuadrilla/XP/OrdenTrabajo) se conserva como overlay opcional.
"""
from datetime import datetime, date
from enum import Enum
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey,
    Enum as SQLEnum, Text, Numeric, event,
)
from sqlalchemy.orm import relationship, Session
from app.database import Base


# ════════════════════════════════════════════════════════════════════
# ENUMS
# ════════════════════════════════════════════════════════════════════

class UserRole(str, Enum):
    super_admin = "super_admin"  # único rol total mientras no haya jerarquía
    admin_finanzas = "admin_finanzas"
    admin = "admin"
    supervisor = "supervisor"
    usuario_bot = "usuario_bot"


class UserStatus(str, Enum):
    active = "active"
    pending = "pending"
    rejected = "rejected"


class TipoFacturacion(str, Enum):
    """Régimen de facturación de la obra (heredado del cliente, override posible)."""
    TOTAL_BLANCO = "TOTAL_BLANCO"
    TOTAL_NEGRO = "TOTAL_NEGRO"
    MIXTA = "MIXTA"
    SIN_DEFINIR = "SIN_DEFINIR"


class ObraStatus(str, Enum):
    EN_CURSO = "EN_CURSO"
    PAUSADA = "PAUSADA"
    FINALIZADA = "FINALIZADA"
    CANCELADA = "CANCELADA"
    # Compat (lúdico)
    planificacion = "planificacion"


class ObraSalud(str, Enum):
    """Capa lúdica — se calcula a partir de progreso y alertas."""
    optimo = "optimo"
    atencion = "atencion"
    critico = "critico"


class EtapaEstado(str, Enum):
    PENDIENTE = "PENDIENTE"
    EN_EJECUCION = "EN_EJECUCION"
    EJECUTADA = "EJECUTADA"
    FACTURADA = "FACTURADA"
    COBRADA = "COBRADA"


class TipoMovimiento(str, Enum):
    INGRESO = "INGRESO"
    EGRESO = "EGRESO"


class OrigenIngreso(str, Enum):
    ANTICIPO_CLIENTE = "ANTICIPO_CLIENTE"
    CERTIFICADO_ETAPA = "CERTIFICADO_ETAPA"
    PAGO_FINAL = "PAGO_FINAL"
    AJUSTE_CONTRATO = "AJUSTE_CONTRATO"
    APORTE_SOCIO_RCA = "APORTE_SOCIO_RCA"
    DEVOLUCION_PROVEEDOR = "DEVOLUCION_PROVEEDOR"


class CategoriaEgreso(str, Enum):
    MANO_DE_OBRA = "MANO_DE_OBRA"
    MATERIALES = "MATERIALES"
    SUBCONTRATO = "SUBCONTRATO"
    SERVICIO_EXTERNO = "SERVICIO_EXTERNO"
    GASTO_DIRECTO_OBRA = "GASTO_DIRECTO_OBRA"
    HERRAMIENTA_EQUIPO = "HERRAMIENTA_EQUIPO"
    APORTE_PRESTAMO = "APORTE_PRESTAMO"


class MedioPago(str, Enum):
    EFECTIVO = "EFECTIVO"
    TRANSFERENCIA = "TRANSFERENCIA"
    CHEQUE_PROPIO = "CHEQUE_PROPIO"
    CHEQUE_TERCERO = "CHEQUE_TERCERO"
    DEPOSITO_BANCARIO = "DEPOSITO_BANCARIO"


class EstadoMovimiento(str, Enum):
    """Etiqueta operativa. NO afecta el saldo (R1 del doc)."""
    CONFIRMADO = "CONFIRMADO"
    A_REVISAR = "A_REVISAR"


class EstadoDevolucion(str, Enum):
    PENDIENTE = "PENDIENTE"
    DEVUELTO_PARCIAL = "DEVUELTO_PARCIAL"
    DEVUELTO_TOTAL = "DEVUELTO_TOTAL"


class TipoComprobante(str, Enum):
    FC_A = "FC_A"
    FC_B = "FC_B"
    FC_C = "FC_C"
    NC_A = "NC_A"
    NC_B = "NC_B"
    ND_A = "ND_A"
    ND_B = "ND_B"
    RECIBO_X = "RECIBO_X"
    REMITO = "REMITO"


class EstadoFiscal(str, Enum):
    VALIDO = "VALIDO"
    SIN_CAE = "SIN_CAE"
    VENCIDO = "VENCIDO"
    ANULADO = "ANULADO"


class TipoRetencion(str, Enum):
    GANANCIAS = "GANANCIAS"
    IIBB = "IIBB"
    IVA_RETENCION = "IVA_RETENCION"
    SUSS = "SUSS"


class CanalCarga(str, Enum):
    whatsapp = "whatsapp"
    web = "web"
    automatico = "automatico"
    agente_ia = "agente_ia"


class AgentActionStatus(str, Enum):
    """Ciclo de vida de una acción del agente IA.

    - executed: tool de lectura o no-confirmable, ejecutada al toque.
    - pending: tool sensible que requiere confirmación humana — payload guardado, NO ejecutada.
    - confirmed: confirmada por el humano y ejecutada con éxito.
    - cancelled: el humano canceló antes de que se ejecutara.
    """
    executed = "executed"
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"


class OutboundMessageStatus(str, Enum):
    """Estado de un mensaje saliente (WhatsApp / SMS / Email)."""
    log_only = "log_only"  # provider en modo log_only — no se envió, queda registrado
    pending = "pending"    # encolado pero aún no enviado
    sent = "sent"          # confirmación del provider
    failed = "failed"      # falló el envío


# Capa lúdica
class FrenteEstado(str, Enum):
    pendiente = "pendiente"
    en_progreso = "en_progreso"
    bloqueado = "bloqueado"
    completado = "completado"


class TaskStatus(str, Enum):
    pendiente = "pendiente"
    en_progreso = "en_progreso"
    completada = "completada"
    bloqueada = "bloqueada"


class UbicacionStockTipo(str, Enum):
    """Dónde está físicamente el material (Sprint 9)."""
    deposito_propio = "deposito_propio"           # depósito de RCA, sin obra asignada
    en_obra = "en_obra"                           # ya retirado y entregado a una obra
    comprado_no_retirado = "comprado_no_retirado" # facturado/pagado pero sigue en el proveedor


class EstadoPresupuesto(str, Enum):
    """Sprint 10."""
    borrador = "borrador"
    aprobado = "aprobado"
    cerrado = "cerrado"


class EventoTipo(str, Enum):
    avance = "avance"
    material_llegada = "material_llegada"
    incidente = "incidente"
    inspeccion = "inspeccion"
    foto = "foto"
    hito = "hito"
    otro = "otro"


# ════════════════════════════════════════════════════════════════════
# USUARIOS
# ════════════════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    last_name = Column(String)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String)
    password_hash = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.super_admin, nullable=False)
    status = Column(SQLEnum(UserStatus), default=UserStatus.active, nullable=False)
    is_active = Column(Boolean, default=True)
    avatar = Column(String)
    xp = Column(Integer, default=0)
    onboarding_step = Column(Integer, default=0)
    # Sprint 11: vinculación con bot de Telegram
    telegram_chat_id = Column(String, unique=True, index=True)  # int de Telegram como string
    telegram_username = Column(String)
    telegram_vinculacion_code = Column(String)  # código temporal generado por admin
    telegram_vinculacion_exp = Column(DateTime)  # expira a los 15 min
    created_at = Column(DateTime, default=datetime.utcnow)


# ════════════════════════════════════════════════════════════════════
# FISCAL — RÉGIMEN Y CLIENTES
# ════════════════════════════════════════════════════════════════════

class RegimenFiscal(Base):
    """Configuración fiscal: Responsable Inscripto, Monotributo, Exento, etc."""
    __tablename__ = "regimenes_fiscales"
    id = Column(Integer, primary_key=True)
    codigo = Column(String(30), unique=True, nullable=False)  # RI, MT, EX, CF
    nombre = Column(String(100), nullable=False)
    iva_default = Column(Numeric(5, 4), default=0.21)  # alícuota por defecto
    aplica_iibb = Column(Boolean, default=True)
    aplica_ganancias = Column(Boolean, default=True)
    descripcion = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Cliente(Base):
    """Cliente final de las obras. Define el régimen fiscal por defecto."""
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(200), nullable=False, index=True)
    cuit = Column(String(13), index=True)
    razon_social = Column(String(200))
    direccion = Column(String(300))
    email = Column(String(200))
    telefono = Column(String(50))
    tipo = Column(String(50))  # publico, privado_ri, privado_mt, particular
    regimen_fiscal_id = Column(Integer, ForeignKey("regimenes_fiscales.id"))
    notas = Column(Text)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    regimen_fiscal = relationship("RegimenFiscal")
    obras = relationship("Obra", back_populates="cliente")


# ════════════════════════════════════════════════════════════════════
# OBRA + ETAPAS
# ════════════════════════════════════════════════════════════════════

class Obra(Base):
    """Cada obra es un proyecto. Ancla del módulo financiero y operativo.

    Sigue el spec del doc — agrega cliente_id, tipo_facturacion, regimen_fiscal_id,
    monto_contrato. Mantiene campos lúdicos (icono, color, salud, progreso).
    """
    __tablename__ = "obras"
    id = Column(Integer, primary_key=True)
    codigo = Column(String(20), unique=True, nullable=False)  # IDS, SP, CONST
    nombre = Column(String(200), nullable=False)

    # Cliente y régimen fiscal
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    regimen_fiscal_id = Column(Integer, ForeignKey("regimenes_fiscales.id"))  # override opcional
    tipo_facturacion = Column(SQLEnum(TipoFacturacion), default=TipoFacturacion.SIN_DEFINIR, nullable=False)

    # Datos de proyecto
    direccion = Column(String(300))
    ciudad = Column(String(100))
    descripcion = Column(Text)
    monto_contrato = Column(Numeric(15, 2))
    fecha_inicio = Column(Date)
    fecha_fin_estimada = Column(Date)
    estado = Column(SQLEnum(ObraStatus), default=ObraStatus.EN_CURSO, nullable=False)

    # Capa lúdica (cosmética — no afecta finanzas)
    color = Column(String(20), default="#1E2B5E")
    icono = Column(String(20), default="🏗️")
    salud = Column(SQLEnum(ObraSalud), default=ObraSalud.optimo)
    progreso = Column(Float, default=0.0)
    superficie_m2 = Column(Float, default=0)
    pisos = Column(Integer, default=1)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cliente = relationship("Cliente", back_populates="obras")
    regimen_fiscal = relationship("RegimenFiscal")
    etapas = relationship("EtapaObra", back_populates="obra", cascade="all, delete-orphan")
    movimientos = relationship("MovimientoObra", back_populates="obra", cascade="all, delete-orphan")
    aportes = relationship("AporteSocio", back_populates="obra", cascade="all, delete-orphan")
    comprobantes = relationship("Comprobante", back_populates="obra", cascade="all, delete-orphan")
    notas = relationship("NotaObra", back_populates="obra", cascade="all, delete-orphan")
    # Capa lúdica
    frentes = relationship("Frente", back_populates="obra", cascade="all, delete-orphan")
    eventos = relationship("Evento", back_populates="obra", cascade="all, delete-orphan")
    ordenes = relationship("OrdenTrabajo", back_populates="obra", cascade="all, delete-orphan")


class EtapaObra(Base):
    """Divide la obra en etapas con monto contractual y cobro esperado."""
    __tablename__ = "etapas_obra"
    id = Column(Integer, primary_key=True)
    obra_id = Column(Integer, ForeignKey("obras.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(150), nullable=False)  # "Anticipo", "Etapa 1 - Estructura"
    nro_etapa = Column(Integer, nullable=False)  # 0 = anticipo, 1+ = sucesivas
    monto_contractual = Column(Numeric(15, 2))
    porcentaje_avance = Column(Numeric(5, 2))  # % de la obra
    estado = Column(SQLEnum(EtapaEstado), default=EtapaEstado.PENDIENTE, nullable=False)
    fecha_estimada = Column(Date)  # de cobro
    fecha_cobro_real = Column(Date)
    notas = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    obra = relationship("Obra", back_populates="etapas")


# ════════════════════════════════════════════════════════════════════
# MOVIMIENTOS — TABLA CENTRAL
# ════════════════════════════════════════════════════════════════════

class MovimientoObra(Base):
    """TABLA CENTRAL del sistema. Cada fila = un ingreso o egreso de obra.

    Saldo = SUM(INGRESO.monto) - SUM(EGRESO.monto). estado NO filtra el saldo (R1).
    """
    __tablename__ = "movimientos_obra"
    id = Column(Integer, primary_key=True)
    obra_id = Column(Integer, ForeignKey("obras.id", ondelete="CASCADE"), nullable=False, index=True)
    etapa_id = Column(Integer, ForeignKey("etapas_obra.id"), index=True)  # NULL para egresos no atados a etapa

    fecha = Column(Date, nullable=False, index=True)  # cuándo ocurrió, NO cuándo se cargó
    tipo = Column(SQLEnum(TipoMovimiento), nullable=False, index=True)
    origen_ingreso = Column(SQLEnum(OrigenIngreso))  # solo si tipo=INGRESO
    categoria_egreso = Column(SQLEnum(CategoriaEgreso))  # solo si tipo=EGRESO

    concepto = Column(String(300), nullable=False)
    monto = Column(Numeric(15, 2), nullable=False)  # siempre positivo

    # Pago
    medio_pago = Column(SQLEnum(MedioPago), nullable=False)
    bancarizado = Column(Boolean, default=False, nullable=False)  # calculado en evento
    nro_cheque = Column(String(30))
    banco = Column(String(100))
    fecha_vto_cheque = Column(Date)  # crítico para R3 (saldo sale al vto)

    # Comprobante
    tiene_comprobante = Column(Boolean, default=False, nullable=False)
    comprobante_id = Column(Integer, ForeignKey("comprobantes.id"))

    # Aporte vinculado
    aporte_socio_id = Column(Integer, ForeignKey("aportes_socios.id"))

    # Vinculación a proveedor (opcional, cuando aplica)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"))

    # Estado y trazabilidad
    estado = Column(SQLEnum(EstadoMovimiento), default=EstadoMovimiento.CONFIRMADO, nullable=False)
    hoja_fisica = Column(String(100))  # "Hoja 15 - 16/03/26"
    canal = Column(SQLEnum(CanalCarga), default=CanalCarga.web, nullable=False)
    cargado_por = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    obra = relationship("Obra", back_populates="movimientos")
    etapa = relationship("EtapaObra")
    comprobante = relationship("Comprobante", foreign_keys=[comprobante_id])
    aporte = relationship("AporteSocio", foreign_keys=[aporte_socio_id], back_populates="movimientos_generados")
    proveedor = relationship("Proveedor")
    cargador = relationship("User", foreign_keys=[cargado_por])
    retenciones = relationship("RetencionSufrida", back_populates="movimiento", cascade="all, delete-orphan")


# Evento SQLAlchemy: setear `bancarizado` automáticamente según medio_pago
@event.listens_for(MovimientoObra, "before_insert")
@event.listens_for(MovimientoObra, "before_update")
def _set_bancarizado(mapper, connection, target):
    if target.medio_pago is None:
        target.bancarizado = False
    elif target.medio_pago == MedioPago.EFECTIVO:
        target.bancarizado = False
    else:
        target.bancarizado = True
    # tiene_comprobante derivado de comprobante_id
    target.tiene_comprobante = target.comprobante_id is not None


# ════════════════════════════════════════════════════════════════════
# APORTES DE SOCIOS
# ════════════════════════════════════════════════════════════════════

class Socio(Base):
    """Socio de RCA. Persona o entidad con participación en la empresa.

    Sprint 7 — antes se usaba `User` con rol admin_finanzas como proxy.
    Ahora tiene tabla propia con datos fiscales y participación. Puede
    opcionalmente vincularse a un `User` si el socio también tiene cuenta
    en la plataforma.
    """
    __tablename__ = "socios"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(150), nullable=False)
    apellido = Column(String(150))
    cuit = Column(String(13), index=True)
    email = Column(String(200))
    telefono = Column(String(50))
    participacion_pct = Column(Numeric(5, 2))  # % de participación en la sociedad
    activo = Column(Boolean, default=True, nullable=False)
    notas = Column(Text)
    # Vínculo opcional a User (si el socio tiene cuenta en la plataforma)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])
    aportes = relationship("AporteSocio", back_populates="socio", cascade="all, delete-orphan")


class AporteSocio(Base):
    """Préstamo interno de un socio (o RCA) a una obra. Obliga a reintegro."""
    __tablename__ = "aportes_socios"
    id = Column(Integer, primary_key=True)
    obra_id = Column(Integer, ForeignKey("obras.id", ondelete="CASCADE"), nullable=False)
    socio_id = Column(Integer, ForeignKey("socios.id"), nullable=False)  # Sprint 7: FK a Socio propio
    etapa_reintegro_id = Column(Integer, ForeignKey("etapas_obra.id"))  # cuándo se prevé devolver

    fecha_aporte = Column(Date, nullable=False)
    monto = Column(Numeric(15, 2), nullable=False)
    motivo = Column(String(300), nullable=False)
    medio_pago = Column(SQLEnum(MedioPago), nullable=False)

    estado_devolucion = Column(SQLEnum(EstadoDevolucion), default=EstadoDevolucion.PENDIENTE, nullable=False)
    monto_devuelto = Column(Numeric(15, 2), default=0, nullable=False)
    fecha_devolucion = Column(Date)
    notas = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    obra = relationship("Obra", back_populates="aportes")
    socio = relationship("Socio", back_populates="aportes")
    movimientos_generados = relationship(
        "MovimientoObra", foreign_keys="[MovimientoObra.aporte_socio_id]", back_populates="aporte",
    )


# ════════════════════════════════════════════════════════════════════
# COMPROBANTES (AFIP)
# ════════════════════════════════════════════════════════════════════

class Comprobante(Base):
    __tablename__ = "comprobantes"
    id = Column(Integer, primary_key=True)
    obra_id = Column(Integer, ForeignKey("obras.id", ondelete="CASCADE"), nullable=False)
    tipo_comprobante = Column(SQLEnum(TipoComprobante), nullable=False)
    punto_venta = Column(Integer)  # NULL si es comprobante recibido
    nro_comprobante = Column(String(20), nullable=False)  # 00001-00000001
    fecha_emision = Column(Date, nullable=False)
    cuit_emisor = Column(String(13), nullable=False)
    cuit_receptor = Column(String(13), nullable=False)

    neto_gravado = Column(Numeric(15, 2), default=0, nullable=False)
    neto_no_gravado = Column(Numeric(15, 2), default=0, nullable=False)
    iva_21 = Column(Numeric(15, 2), default=0, nullable=False)
    iva_105 = Column(Numeric(15, 2), default=0, nullable=False)
    total = Column(Numeric(15, 2), nullable=False)

    cae = Column(String(20))
    cae_vencimiento = Column(Date)
    es_venta = Column(Boolean, nullable=False)  # TRUE = emitido (venta), FALSE = recibido (compra)
    estado_fiscal = Column(SQLEnum(EstadoFiscal), default=EstadoFiscal.VALIDO, nullable=False)

    archivo_url = Column(String(500))  # PDF/imagen del comprobante
    notas = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    obra = relationship("Obra", back_populates="comprobantes")


# ════════════════════════════════════════════════════════════════════
# RETENCIONES
# ════════════════════════════════════════════════════════════════════

class RetencionSufrida(Base):
    """Retenciones que el cliente practica al cobrar."""
    __tablename__ = "retenciones_sufridas"
    id = Column(Integer, primary_key=True)
    movimiento_id = Column(Integer, ForeignKey("movimientos_obra.id", ondelete="CASCADE"), nullable=False)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=False)  # redundante, pero cómodo
    tipo_retencion = Column(SQLEnum(TipoRetencion), nullable=False)
    alicuota = Column(Numeric(5, 4), nullable=False)  # 0.0200 = 2%
    base_calculo = Column(Numeric(15, 2), nullable=False)
    monto_retenido = Column(Numeric(15, 2), nullable=False)
    nro_constancia = Column(String(50))
    fecha_retencion = Column(Date, nullable=False)
    agente_retencion = Column(String(200))
    cuit_agente = Column(String(13))
    created_at = Column(DateTime, default=datetime.utcnow)

    movimiento = relationship("MovimientoObra", back_populates="retenciones")


# ════════════════════════════════════════════════════════════════════
# NOTAS
# ════════════════════════════════════════════════════════════════════

class NotaObra(Base):
    """Notas y observaciones de obra (reemplaza columna de notas en hojas físicas)."""
    __tablename__ = "notas_obra"
    id = Column(Integer, primary_key=True)
    obra_id = Column(Integer, ForeignKey("obras.id", ondelete="CASCADE"), nullable=False)
    movimiento_id = Column(Integer, ForeignKey("movimientos_obra.id"))  # opcional: nota sobre un mov específico
    texto = Column(Text, nullable=False)
    autor_id = Column(Integer, ForeignKey("users.id"))
    importante = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    obra = relationship("Obra", back_populates="notas")
    autor = relationship("User", foreign_keys=[autor_id])


# ════════════════════════════════════════════════════════════════════
# CAPA LÚDICA / OPERATIVA (mantenida del modelo anterior)
# ════════════════════════════════════════════════════════════════════

class Frente(Base):
    """Sub-mapa operativo dentro de la obra (cimientos, terminaciones, etc.)."""
    __tablename__ = "frentes"
    id = Column(Integer, primary_key=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=False)
    nombre = Column(String, nullable=False)
    tipo = Column(String)
    icono = Column(String, default="⬛")
    estado = Column(SQLEnum(FrenteEstado), default=FrenteEstado.pendiente)
    progreso = Column(Float, default=0.0)
    cuadrilla_id = Column(Integer, ForeignKey("cuadrillas.id"))
    fecha_inicio = Column(Date)
    fecha_fin_estimada = Column(Date)
    notas = Column(Text)

    obra = relationship("Obra", back_populates="frentes")
    cuadrilla = relationship("Cuadrilla", back_populates="frentes")


class Cuadrilla(Base):
    """Equipo operativo. Capa lúdica: stats RPG (XP/nivel/eficiencia)."""
    __tablename__ = "cuadrillas"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    especialidad = Column(String)
    avatar = Column(String, default="👷")
    color = Column(String, default="#22C55E")
    cantidad_miembros = Column(Integer, default=1)
    nivel = Column(Integer, default=1)
    experiencia = Column(Integer, default=0)
    eficiencia = Column(Float, default=80.0)
    capataz_id = Column(Integer, ForeignKey("users.id"))
    telefono = Column(String)
    activa = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    frentes = relationship("Frente", back_populates="cuadrilla")
    capataz = relationship("User")


class Material(Base):
    """Inventario de insumos (no es patrimonio — para herramientas ver herramientas_en_obra)."""
    __tablename__ = "materiales"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    categoria = Column(String, index=True)
    unidad = Column(String, default="u")
    stock = Column(Float, default=0)
    stock_minimo = Column(Float, default=0)
    precio_unitario = Column(Float, default=0)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"))
    icono = Column(String, default="📦")
    created_at = Column(DateTime, default=datetime.utcnow)

    proveedor = relationship("Proveedor", back_populates="materiales")
    movimientos = relationship("MovimientoMaterial", back_populates="material", cascade="all, delete-orphan")


class MovimientoMaterial(Base):
    """Ingreso/consumo de materiales (NO es lo mismo que movimientos_obra financiero)."""
    __tablename__ = "movimientos_material"
    id = Column(Integer, primary_key=True)
    material_id = Column(Integer, ForeignKey("materiales.id"), nullable=False)
    obra_id = Column(Integer, ForeignKey("obras.id"))
    tipo = Column(String, nullable=False)  # ingreso, consumo, transferencia
    cantidad = Column(Float, nullable=False)
    nota = Column(Text)
    fecha = Column(DateTime, default=datetime.utcnow)
    usuario_id = Column(Integer, ForeignKey("users.id"))

    material = relationship("Material", back_populates="movimientos")


class StockMaterial(Base):
    """Stock por ubicación física (Sprint 9).

    Una fila por combinación material + (tipo_ubicación, ref). Ejemplos:
    - (material=cemento, tipo=deposito_propio, ref=null): 50 bolsas en depósito.
    - (material=cemento, tipo=en_obra, ref=obra_id=3): 20 bolsas en obra IDS.
    - (material=cemento, tipo=comprado_no_retirado, ref=proveedor_id=2): 100 pendientes de retiro en Holcim.

    El campo Material.stock queda como cache del total (deposito + en_obra), sin contar
    pendientes de retiro. Se recalcula vía evento.
    """
    __tablename__ = "stock_material"
    id = Column(Integer, primary_key=True)
    material_id = Column(Integer, ForeignKey("materiales.id"), nullable=False, index=True)
    ubicacion_tipo = Column(SQLEnum(UbicacionStockTipo), nullable=False, index=True)
    ubicacion_ref = Column(Integer)  # obra_id | proveedor_id | null
    cantidad = Column(Float, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    material = relationship("Material")


class Presupuesto(Base):
    """Sprint 10 — Presupuesto de materiales por obra."""
    __tablename__ = "presupuestos"
    id = Column(Integer, primary_key=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=False, index=True)
    nombre = Column(String, nullable=False)
    estado = Column(SQLEnum(EstadoPresupuesto), default=EstadoPresupuesto.borrador, nullable=False)
    total_estimado = Column(Float, default=0)
    notas = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    aprobado_at = Column(DateTime)
    created_by_id = Column(Integer, ForeignKey("users.id"))

    obra = relationship("Obra")
    items = relationship("PresupuestoItem", back_populates="presupuesto", cascade="all, delete-orphan")
    created_by = relationship("User")


class PresupuestoItem(Base):
    __tablename__ = "presupuesto_items"
    id = Column(Integer, primary_key=True)
    presupuesto_id = Column(Integer, ForeignKey("presupuestos.id", ondelete="CASCADE"), nullable=False)
    material_id = Column(Integer, ForeignKey("materiales.id"), nullable=False)
    cantidad = Column(Float, nullable=False, default=0)
    precio_unitario_estimado = Column(Float, nullable=False, default=0)
    subtotal = Column(Float, nullable=False, default=0)

    presupuesto = relationship("Presupuesto", back_populates="items")
    material = relationship("Material")


class Proveedor(Base):
    __tablename__ = "proveedores"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    cuit = Column(String)
    telefono = Column(String)
    email = Column(String)
    rubro = Column(String)
    rating = Column(Float, default=4.0)
    plazo_entrega_dias = Column(Integer, default=3)
    moroso = Column(Boolean, default=False)
    notas = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    materiales = relationship("Material", back_populates="proveedor")


class OrdenTrabajo(Base):
    """Quest operativa. Capa lúdica con XP reward."""
    __tablename__ = "ordenes_trabajo"
    id = Column(Integer, primary_key=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=False)
    frente_id = Column(Integer, ForeignKey("frentes.id"))
    cuadrilla_id = Column(Integer, ForeignKey("cuadrillas.id"))
    titulo = Column(String, nullable=False)
    descripcion = Column(Text)
    prioridad = Column(String, default="normal")
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.pendiente)
    xp_reward = Column(Integer, default=10)
    fecha_limite = Column(Date)
    completada_at = Column(DateTime)
    creada_por_id = Column(Integer, ForeignKey("users.id"))
    canal_creacion = Column(SQLEnum(CanalCarga), default=CanalCarga.web)
    created_at = Column(DateTime, default=datetime.utcnow)

    obra = relationship("Obra", back_populates="ordenes")


class Evento(Base):
    """Actividad / log del feed."""
    __tablename__ = "eventos"
    id = Column(Integer, primary_key=True)
    obra_id = Column(Integer, ForeignKey("obras.id"))
    frente_id = Column(Integer, ForeignKey("frentes.id"))
    tipo = Column(SQLEnum(EventoTipo), default=EventoTipo.otro)
    titulo = Column(String, nullable=False)
    descripcion = Column(Text)
    foto_url = Column(String)
    canal = Column(SQLEnum(CanalCarga), default=CanalCarga.web)
    usuario_id = Column(Integer, ForeignKey("users.id"))
    es_critico = Column(Boolean, default=False)
    fecha = Column(DateTime, default=datetime.utcnow, index=True)

    obra = relationship("Obra", back_populates="eventos")


# ════════════════════════════════════════════════════════════════════
# AGENTE IA (sin cambios)
# ════════════════════════════════════════════════════════════════════

class AgentSession(Base):
    __tablename__ = "agent_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    messages_json = Column(Text, default="[]")
    last_message_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentAction(Base):
    __tablename__ = "agent_actions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id"))
    tool_name = Column(String, nullable=False, index=True)
    tool_input_json = Column(Text)
    tool_output_json = Column(Text)
    ok = Column(Boolean, default=True)
    error = Column(Text)
    canal = Column(SQLEnum(CanalCarga), default=CanalCarga.web)
    # Sprint 2: confirmación humana para tools sensibles.
    status = Column(SQLEnum(AgentActionStatus), default=AgentActionStatus.executed, nullable=False, index=True)
    confirmed_by = Column(Integer, ForeignKey("users.id"))
    confirmed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    confirmer = relationship("User", foreign_keys=[confirmed_by])


# ════════════════════════════════════════════════════════════════════
# WHATSAPP OUTBOUND (Sprint 4)
# ════════════════════════════════════════════════════════════════════

class OutboundMessage(Base):
    """Registro de cada mensaje que sale de la plataforma (WhatsApp por ahora).

    Soporta múltiples providers (log_only por defecto, twilio, cloud_api).
    Si el provider es log_only, el mensaje se persiste con status=log_only y
    NO se envía. Si es twilio/cloud_api, se hace la llamada y se actualiza el
    status según el resultado.
    """
    __tablename__ = "outbound_messages"
    id = Column(Integer, primary_key=True)
    canal = Column(String, default="whatsapp", nullable=False)
    destinatario = Column(String, nullable=False, index=True)  # +5491100000000
    mensaje = Column(Text, nullable=False)
    foto_url = Column(String)
    provider = Column(String, nullable=False)  # log_only / twilio / cloud_api
    status = Column(SQLEnum(OutboundMessageStatus), default=OutboundMessageStatus.pending, nullable=False, index=True)
    provider_message_id = Column(String)  # SID de Twilio, ID de Cloud API, etc.
    error = Column(Text)
    # Contexto: por qué se envió esto
    notification_type = Column(String, index=True)  # cheque_venciendo / evento_critico / semanal / asignacion / agente_ia / manual / approval / slash_response
    # Idempotency key: opcional, sirve para dedupear notificaciones automáticas.
    # Ej: cheque_venciendo:movimiento=42:vto=2026-05-23
    context_key = Column(String, index=True)
    obra_id = Column(Integer, ForeignKey("obras.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    related_action_id = Column(Integer, ForeignKey("agent_actions.id"))
    sent_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
