from datetime import datetime, date
from enum import Enum
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey,
    Enum as SQLEnum, Text
)
from sqlalchemy.orm import relationship
from app.database import Base


# ─── Enums ───
class UserRole(str, Enum):
    admin_finanzas = "admin_finanzas"
    admin = "admin"           # Project Manager
    supervisor = "supervisor"  # Jefe de obra / capataz con app web
    usuario_bot = "usuario_bot"  # Capataz/operario solo WhatsApp


class UserStatus(str, Enum):
    active = "active"
    pending = "pending"
    rejected = "rejected"


class ObraStatus(str, Enum):
    planificacion = "planificacion"
    en_obra = "en_obra"
    pausada = "pausada"
    finalizada = "finalizada"


class ObraSalud(str, Enum):
    optimo = "optimo"        # verde
    atencion = "atencion"    # amarillo
    critico = "critico"      # rojo


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


class EventoTipo(str, Enum):
    avance = "avance"
    material_llegada = "material_llegada"
    incidente = "incidente"
    inspeccion = "inspeccion"
    foto = "foto"
    hito = "hito"
    otro = "otro"


class CanalCarga(str, Enum):
    whatsapp = "whatsapp"
    web = "web"
    automatico = "automatico"


# ─── Modelos ───
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    last_name = Column(String)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String)
    password_hash = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.usuario_bot, nullable=False)
    status = Column(SQLEnum(UserStatus), default=UserStatus.active, nullable=False)
    is_active = Column(Boolean, default=True)
    avatar = Column(String)  # emoji o url
    xp = Column(Integer, default=0)  # gamification
    onboarding_step = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Obra(Base):
    """Cada obra es un 'micro-mundo' con su propio mapa, frentes y stats."""
    __tablename__ = "obras"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    codigo = Column(String, unique=True)  # ej: "TA-2026-01"
    direccion = Column(String)
    ciudad = Column(String)
    cliente = Column(String)
    descripcion = Column(Text)
    color = Column(String, default="#3B82F6")  # color de identidad visual
    icono = Column(String, default="🏗️")

    # Stats del "mundo"
    status = Column(SQLEnum(ObraStatus), default=ObraStatus.planificacion)
    salud = Column(SQLEnum(ObraSalud), default=ObraSalud.optimo)
    progreso = Column(Float, default=0.0)  # 0-100, calculado de frentes
    presupuesto_total = Column(Float, default=0)
    presupuesto_consumido = Column(Float, default=0)
    fecha_inicio = Column(Date)
    fecha_fin_estimada = Column(Date)

    superficie_m2 = Column(Float, default=0)
    pisos = Column(Integer, default=1)

    created_at = Column(DateTime, default=datetime.utcnow)

    frentes = relationship("Frente", back_populates="obra", cascade="all, delete-orphan")
    eventos = relationship("Evento", back_populates="obra", cascade="all, delete-orphan")
    ordenes = relationship("OrdenTrabajo", back_populates="obra", cascade="all, delete-orphan")


class Frente(Base):
    """Sub-mapa dentro de una obra (cimientos, estructura, terminaciones)."""
    __tablename__ = "frentes"
    id = Column(Integer, primary_key=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=False)
    nombre = Column(String, nullable=False)
    tipo = Column(String)  # cimientos, estructura, mamposteria, instalaciones, terminaciones
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
    """Equipo de trabajo - 'personaje' del juego con stats."""
    __tablename__ = "cuadrillas"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    especialidad = Column(String)  # albañilería, electricidad, plomería, pintura, herrería
    avatar = Column(String, default="👷")
    color = Column(String, default="#22C55E")

    # Stats RPG
    cantidad_miembros = Column(Integer, default=1)
    nivel = Column(Integer, default=1)
    experiencia = Column(Integer, default=0)
    eficiencia = Column(Float, default=80.0)  # 0-100, calculado de tareas terminadas a tiempo

    capataz_id = Column(Integer, ForeignKey("users.id"))
    telefono = Column(String)  # WhatsApp del grupo
    activa = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    frentes = relationship("Frente", back_populates="cuadrilla")
    capataz = relationship("User")


class Material(Base):
    __tablename__ = "materiales"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    categoria = Column(String, index=True)  # cemento, hierro, ladrillo, áridos, instalaciones, terminaciones
    unidad = Column(String, default="u")  # bolsa, m3, tn, u
    stock = Column(Float, default=0)
    stock_minimo = Column(Float, default=0)  # alerta si baja de aquí
    precio_unitario = Column(Float, default=0)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"))
    icono = Column(String, default="📦")
    created_at = Column(DateTime, default=datetime.utcnow)

    proveedor = relationship("Proveedor", back_populates="materiales")
    movimientos = relationship("MovimientoMaterial", back_populates="material", cascade="all, delete-orphan")


class MovimientoMaterial(Base):
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


class Proveedor(Base):
    __tablename__ = "proveedores"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    cuit = Column(String)
    telefono = Column(String)
    email = Column(String)
    rubro = Column(String)  # cemento, hierro, herramientas, sub-contratista
    rating = Column(Float, default=4.0)  # 0-5 estrellas
    plazo_entrega_dias = Column(Integer, default=3)
    moroso = Column(Boolean, default=False)
    notas = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    materiales = relationship("Material", back_populates="proveedor")


class OrdenTrabajo(Base):
    """Quest del juego: tarea asignada a una cuadrilla en una obra."""
    __tablename__ = "ordenes_trabajo"
    id = Column(Integer, primary_key=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=False)
    frente_id = Column(Integer, ForeignKey("frentes.id"))
    cuadrilla_id = Column(Integer, ForeignKey("cuadrillas.id"))
    titulo = Column(String, nullable=False)
    descripcion = Column(Text)
    prioridad = Column(String, default="normal")  # baja, normal, alta, critica
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.pendiente)
    xp_reward = Column(Integer, default=10)  # gamification
    fecha_limite = Column(Date)
    completada_at = Column(DateTime)
    creada_por_id = Column(Integer, ForeignKey("users.id"))
    canal_creacion = Column(SQLEnum(CanalCarga), default=CanalCarga.web)
    created_at = Column(DateTime, default=datetime.utcnow)

    obra = relationship("Obra", back_populates="ordenes")


class Evento(Base):
    """Notificación tipo 'log' del juego: cualquier cosa que pasa en la obra."""
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
    es_critico = Column(Boolean, default=False)  # alerta resaltada
    fecha = Column(DateTime, default=datetime.utcnow, index=True)

    obra = relationship("Obra", back_populates="eventos")


class Gasto(Base):
    __tablename__ = "gastos"
    id = Column(Integer, primary_key=True)
    obra_id = Column(Integer, ForeignKey("obras.id"))
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"))
    categoria = Column(String, nullable=False, index=True)
    monto = Column(Float, nullable=False)
    moneda = Column(String, default="ARS")
    con_iva = Column(Boolean, default=True)
    descripcion = Column(Text)
    fecha = Column(Date, default=date.today)
    pagado = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
