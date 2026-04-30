from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from app.models import (
    UserRole, UserStatus, ObraStatus, ObraSalud, FrenteEstado,
    TaskStatus, EventoTipo, CanalCarga
)


# ─── Auth ───
class UserBase(BaseModel):
    name: str
    last_name: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(min_length=6)
    role: UserRole = UserRole.usuario_bot


class UserOut(UserBase):
    id: int
    role: UserRole
    status: UserStatus
    is_active: bool
    avatar: Optional[str] = None
    xp: int
    onboarding_step: int
    created_at: datetime

    class Config:
        from_attributes = True


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserRoleUpdate(BaseModel):
    role: UserRole


# ─── Obra ───
class ObraIn(BaseModel):
    nombre: str
    codigo: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    cliente: Optional[str] = None
    descripcion: Optional[str] = None
    color: str = "#3B82F6"
    icono: str = "🏗️"
    status: ObraStatus = ObraStatus.planificacion
    presupuesto_total: float = 0
    fecha_inicio: Optional[date] = None
    fecha_fin_estimada: Optional[date] = None
    superficie_m2: float = 0
    pisos: int = 1


class ObraOut(ObraIn):
    id: int
    salud: ObraSalud
    progreso: float
    presupuesto_consumido: float
    created_at: datetime

    class Config:
        from_attributes = True


class ObraDashboard(BaseModel):
    """Resumen rico de una obra para la vista micro-mundo."""
    obra: ObraOut
    frentes_total: int
    frentes_completados: int
    cuadrillas_activas: int
    obreros_total: int
    eventos_recientes: int
    alertas: int
    ordenes_pendientes: int
    presupuesto_pct: float
    dias_restantes: Optional[int] = None


# ─── Frente ───
class FrenteIn(BaseModel):
    obra_id: int
    nombre: str
    tipo: Optional[str] = None
    icono: str = "⬛"
    estado: FrenteEstado = FrenteEstado.pendiente
    progreso: float = 0
    cuadrilla_id: Optional[int] = None
    fecha_inicio: Optional[date] = None
    fecha_fin_estimada: Optional[date] = None
    notas: Optional[str] = None


class FrenteOut(FrenteIn):
    id: int

    class Config:
        from_attributes = True


# ─── Cuadrilla ───
class CuadrillaIn(BaseModel):
    nombre: str
    especialidad: Optional[str] = None
    avatar: str = "👷"
    color: str = "#22C55E"
    cantidad_miembros: int = 1
    capataz_id: Optional[int] = None
    telefono: Optional[str] = None


class CuadrillaOut(CuadrillaIn):
    id: int
    nivel: int
    experiencia: int
    eficiencia: float
    activa: bool

    class Config:
        from_attributes = True


# ─── Material ───
class MaterialIn(BaseModel):
    nombre: str
    categoria: Optional[str] = None
    unidad: str = "u"
    stock: float = 0
    stock_minimo: float = 0
    precio_unitario: float = 0
    proveedor_id: Optional[int] = None
    icono: str = "📦"


class MaterialOut(MaterialIn):
    id: int

    class Config:
        from_attributes = True


class MovimientoIn(BaseModel):
    tipo: str
    cantidad: float
    obra_id: Optional[int] = None
    nota: Optional[str] = None


# ─── Proveedor ───
class ProveedorIn(BaseModel):
    nombre: str
    cuit: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    rubro: Optional[str] = None
    rating: float = 4.0
    plazo_entrega_dias: int = 3
    notas: Optional[str] = None


class ProveedorOut(ProveedorIn):
    id: int
    moroso: bool

    class Config:
        from_attributes = True


# ─── Orden de Trabajo ───
class OrdenIn(BaseModel):
    obra_id: int
    frente_id: Optional[int] = None
    cuadrilla_id: Optional[int] = None
    titulo: str
    descripcion: Optional[str] = None
    prioridad: str = "normal"
    fecha_limite: Optional[date] = None
    xp_reward: int = 10


class OrdenOut(BaseModel):
    id: int
    obra_id: int
    frente_id: Optional[int] = None
    cuadrilla_id: Optional[int] = None
    titulo: str
    descripcion: Optional[str] = None
    prioridad: str
    status: TaskStatus
    xp_reward: int
    fecha_limite: Optional[date] = None
    completada_at: Optional[datetime] = None
    canal_creacion: CanalCarga
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Evento ───
class EventoIn(BaseModel):
    obra_id: Optional[int] = None
    frente_id: Optional[int] = None
    tipo: EventoTipo = EventoTipo.otro
    titulo: str
    descripcion: Optional[str] = None
    foto_url: Optional[str] = None
    es_critico: bool = False


class EventoOut(BaseModel):
    id: int
    obra_id: Optional[int] = None
    frente_id: Optional[int] = None
    tipo: EventoTipo
    titulo: str
    descripcion: Optional[str] = None
    foto_url: Optional[str] = None
    canal: CanalCarga
    es_critico: bool
    usuario_id: Optional[int] = None
    fecha: datetime

    class Config:
        from_attributes = True


# ─── Gasto ───
class GastoIn(BaseModel):
    obra_id: Optional[int] = None
    proveedor_id: Optional[int] = None
    categoria: str
    monto: float
    moneda: str = "ARS"
    con_iva: bool = True
    descripcion: Optional[str] = None
    fecha: Optional[date] = None
    pagado: bool = False


class GastoOut(GastoIn):
    id: int

    class Config:
        from_attributes = True


# ─── Webhook ───
class WhatsAppMessageIn(BaseModel):
    phone: str
    text: str
    token: str
    foto_url: Optional[str] = None


# ─── HUD Global ───
class HudGlobal(BaseModel):
    presupuesto_total: float
    presupuesto_consumido: float
    materiales_total: int
    materiales_criticos: int
    obreros_total: int
    cuadrillas_activas: int
    obras_activas: int
    productividad: float  # avg eficiencia
    alertas_total: int
