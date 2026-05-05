from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from app.models import (
    UserRole, UserStatus, ObraStatus, ObraSalud, FrenteEstado,
    TaskStatus, EventoTipo, CanalCarga,
    TipoFacturacion, EtapaEstado, TipoMovimiento, OrigenIngreso,
    CategoriaEgreso, MedioPago, EstadoMovimiento, EstadoDevolucion,
    TipoComprobante, EstadoFiscal, TipoRetencion,
)


# ════════════════════════════════════════════════════════════════════
# AUTH / USER
# ════════════════════════════════════════════════════════════════════

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


# ════════════════════════════════════════════════════════════════════
# RÉGIMEN FISCAL
# ════════════════════════════════════════════════════════════════════

class RegimenFiscalIn(BaseModel):
    codigo: str
    nombre: str
    iva_default: float = 0.21
    aplica_iibb: bool = True
    aplica_ganancias: bool = True
    descripcion: Optional[str] = None


class RegimenFiscalOut(RegimenFiscalIn):
    id: int

    class Config:
        from_attributes = True


# ════════════════════════════════════════════════════════════════════
# CLIENTE
# ════════════════════════════════════════════════════════════════════

class ClienteIn(BaseModel):
    nombre: str
    cuit: Optional[str] = None
    razon_social: Optional[str] = None
    direccion: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    tipo: Optional[str] = None  # publico, privado_ri, privado_mt, particular
    regimen_fiscal_id: Optional[int] = None
    notas: Optional[str] = None
    activo: bool = True


class ClienteOut(ClienteIn):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ════════════════════════════════════════════════════════════════════
# OBRA
# ════════════════════════════════════════════════════════════════════

class ObraIn(BaseModel):
    codigo: str
    nombre: str
    cliente_id: int
    regimen_fiscal_id: Optional[int] = None
    tipo_facturacion: TipoFacturacion = TipoFacturacion.SIN_DEFINIR

    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    descripcion: Optional[str] = None
    monto_contrato: Optional[float] = None
    fecha_inicio: Optional[date] = None
    fecha_fin_estimada: Optional[date] = None
    estado: ObraStatus = ObraStatus.EN_CURSO

    color: str = "#1E2B5E"
    icono: str = "🏗️"
    superficie_m2: float = 0
    pisos: int = 1


class ObraOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    cliente_id: int
    regimen_fiscal_id: Optional[int] = None
    tipo_facturacion: TipoFacturacion
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    descripcion: Optional[str] = None
    monto_contrato: Optional[float] = None
    fecha_inicio: Optional[date] = None
    fecha_fin_estimada: Optional[date] = None
    estado: ObraStatus
    salud: ObraSalud
    progreso: float
    color: str
    icono: str
    superficie_m2: float
    pisos: int
    created_at: datetime

    class Config:
        from_attributes = True


class ObraDashboard(BaseModel):
    """Resumen rico de una obra."""
    obra: ObraOut
    cliente_nombre: Optional[str] = None
    # Financiero
    monto_contrato: float
    total_ingresos: float
    total_egresos: float
    saldo: float
    aportes_pendientes: float
    cheques_a_vencer: float
    # Operativo / lúdico
    frentes_total: int
    frentes_completados: int
    cuadrillas_activas: int
    obreros_total: int
    eventos_recientes: int
    alertas: int
    ordenes_pendientes: int
    dias_restantes: Optional[int] = None
    # Etapas
    etapas_total: int
    etapas_cobradas: int


# ════════════════════════════════════════════════════════════════════
# ETAPAS
# ════════════════════════════════════════════════════════════════════

class EtapaIn(BaseModel):
    obra_id: int
    nombre: str
    nro_etapa: int
    monto_contractual: Optional[float] = None
    porcentaje_avance: Optional[float] = None
    estado: EtapaEstado = EtapaEstado.PENDIENTE
    fecha_estimada: Optional[date] = None
    fecha_cobro_real: Optional[date] = None
    notas: Optional[str] = None


class EtapaOut(EtapaIn):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ════════════════════════════════════════════════════════════════════
# MOVIMIENTOS — TABLA CENTRAL
# ════════════════════════════════════════════════════════════════════

class MovimientoIn(BaseModel):
    obra_id: int
    etapa_id: Optional[int] = None
    fecha: date
    tipo: TipoMovimiento
    origen_ingreso: Optional[OrigenIngreso] = None
    categoria_egreso: Optional[CategoriaEgreso] = None
    concepto: str
    monto: float = Field(gt=0)
    medio_pago: MedioPago
    nro_cheque: Optional[str] = None
    banco: Optional[str] = None
    fecha_vto_cheque: Optional[date] = None
    comprobante_id: Optional[int] = None
    aporte_socio_id: Optional[int] = None
    proveedor_id: Optional[int] = None
    estado: EstadoMovimiento = EstadoMovimiento.CONFIRMADO
    hoja_fisica: Optional[str] = None
    canal: CanalCarga = CanalCarga.web


class MovimientoOut(BaseModel):
    id: int
    obra_id: int
    etapa_id: Optional[int] = None
    fecha: date
    tipo: TipoMovimiento
    origen_ingreso: Optional[OrigenIngreso] = None
    categoria_egreso: Optional[CategoriaEgreso] = None
    concepto: str
    monto: float
    medio_pago: MedioPago
    bancarizado: bool
    nro_cheque: Optional[str] = None
    banco: Optional[str] = None
    fecha_vto_cheque: Optional[date] = None
    tiene_comprobante: bool
    comprobante_id: Optional[int] = None
    aporte_socio_id: Optional[int] = None
    proveedor_id: Optional[int] = None
    estado: EstadoMovimiento
    hoja_fisica: Optional[str] = None
    canal: CanalCarga
    cargado_por: int
    created_at: datetime

    class Config:
        from_attributes = True


class FlujoCajaSemana(BaseModel):
    semana: date
    ingresos: float
    egresos: float
    saldo_semana: float
    saldo_acumulado: float


# ════════════════════════════════════════════════════════════════════
# APORTES
# ════════════════════════════════════════════════════════════════════

class AporteIn(BaseModel):
    obra_id: int
    socio_id: int
    etapa_reintegro_id: Optional[int] = None
    fecha_aporte: date
    monto: float = Field(gt=0)
    motivo: str
    medio_pago: MedioPago
    notas: Optional[str] = None


class AporteOut(AporteIn):
    id: int
    estado_devolucion: EstadoDevolucion
    monto_devuelto: float
    fecha_devolucion: Optional[date] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AporteDevolucionIn(BaseModel):
    monto: float = Field(gt=0)
    fecha: date
    medio_pago: MedioPago
    notas: Optional[str] = None


# ════════════════════════════════════════════════════════════════════
# COMPROBANTES
# ════════════════════════════════════════════════════════════════════

class ComprobanteIn(BaseModel):
    obra_id: int
    tipo_comprobante: TipoComprobante
    punto_venta: Optional[int] = None
    nro_comprobante: str
    fecha_emision: date
    cuit_emisor: str
    cuit_receptor: str
    neto_gravado: float = 0
    neto_no_gravado: float = 0
    iva_21: float = 0
    iva_105: float = 0
    total: float
    cae: Optional[str] = None
    cae_vencimiento: Optional[date] = None
    es_venta: bool
    estado_fiscal: EstadoFiscal = EstadoFiscal.VALIDO
    archivo_url: Optional[str] = None
    notas: Optional[str] = None


class ComprobanteOut(ComprobanteIn):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ════════════════════════════════════════════════════════════════════
# RETENCIONES
# ════════════════════════════════════════════════════════════════════

class RetencionIn(BaseModel):
    movimiento_id: int
    obra_id: int
    tipo_retencion: TipoRetencion
    alicuota: float
    base_calculo: float
    monto_retenido: float
    nro_constancia: Optional[str] = None
    fecha_retencion: date
    agente_retencion: Optional[str] = None
    cuit_agente: Optional[str] = None


class RetencionOut(RetencionIn):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ════════════════════════════════════════════════════════════════════
# NOTAS
# ════════════════════════════════════════════════════════════════════

class NotaIn(BaseModel):
    obra_id: int
    movimiento_id: Optional[int] = None
    texto: str
    importante: bool = False


class NotaOut(NotaIn):
    id: int
    autor_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ════════════════════════════════════════════════════════════════════
# CAPA LÚDICA / OPERATIVA (sin cambios mayores)
# ════════════════════════════════════════════════════════════════════

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


class MovimientoMaterialIn(BaseModel):
    tipo: str
    cantidad: float
    obra_id: Optional[int] = None
    nota: Optional[str] = None


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


# ════════════════════════════════════════════════════════════════════
# WHATSAPP / HUD
# ════════════════════════════════════════════════════════════════════

class WhatsAppMessageIn(BaseModel):
    phone: str
    text: str
    token: str
    foto_url: Optional[str] = None


class HudGlobal(BaseModel):
    # Financiero (calculado de movimientos_obra)
    monto_contratos_total: float
    total_ingresos: float
    total_egresos: float
    saldo_global: float
    aportes_pendientes: float
    cheques_a_vencer: float
    # Operativo
    obras_total: int
    obras_activas: int
    cuadrillas_activas: int
    obreros_total: int
    materiales_total: int
    materiales_criticos: int
    productividad: float
    alertas_total: int
