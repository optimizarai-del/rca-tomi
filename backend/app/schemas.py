from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models import (
    UserRole, UserStatus, ObraStatus, ObraSalud, FrenteEstado,
    TaskStatus, EventoTipo, CanalCarga,
    TipoFacturacion, EtapaEstado, TipoMovimiento, OrigenIngreso,
    CategoriaEgreso, MedioPago, EstadoMovimiento, EstadoDevolucion,
    TipoComprobante, EstadoFiscal, TipoRetencion,
    RequerimientoEstado,
    LegalidadMovimiento, CobroPagoEstado,
    PlanObraEstado,
    TicketOCREstado,
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
    # Sprint 11
    telegram_chat_id: Optional[str] = None
    telegram_username: Optional[str] = None
    # Sprint 12
    is_demo: bool = False

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
    # Sprint 22 — memoria
    cbu: Optional[str] = None
    alias_bancario: Optional[str] = None
    condiciones_pago: Optional[str] = None
    contacto_secundario: Optional[str] = None
    preferencias: Optional[str] = None


class ClienteOut(ClienteIn):
    id: int
    created_at: datetime
    last_interaction_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Sprint 22: detalle / memoria del cliente ───────────────────────────

class ClienteNotaIn(BaseModel):
    cliente_id: int
    texto: str = Field(min_length=1, max_length=2000)
    importante: bool = False


class ClienteNotaOut(BaseModel):
    id: int
    cliente_id: int
    autor_id: Optional[int] = None
    texto: str
    importante: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ClienteObraResumen(BaseModel):
    """Una obra del cliente con sus números clave."""
    id: int
    codigo: str
    nombre: str
    estado: ObraStatus
    monto_contrato: float = 0
    fecha_inicio: Optional[date] = None
    fecha_fin_estimada: Optional[date] = None
    progreso: float = 0
    # Sprint 21 — totales de la caja contable
    ingresos_cobrado: float = 0
    ingresos_pendiente: float = 0
    saldo_obra: float = 0  # cobrado - pagado consolidado


class ClienteResumenFinanciero(BaseModel):
    """Agregado de todas las obras del cliente."""
    monto_contratos_total: float = 0
    ingresos_cobrado_total: float = 0
    ingresos_pendiente_total: float = 0  # lo que el cliente NOS debe
    egresos_pagado_total: float = 0
    egresos_pendiente_total: float = 0   # lo que nosotros debemos por esta obra (proveedores)
    obras_total: int = 0
    obras_en_curso: int = 0
    obras_finalizadas: int = 0


class ClienteDetalleOut(ClienteOut):
    obras: List[ClienteObraResumen] = []
    resumen_financiero: ClienteResumenFinanciero
    interacciones: List[ClienteNotaOut] = []  # log de notas (renombrado para no chocar con Cliente.notas string)


# ════════════════════════════════════════════════════════════════════
# SOCIO (Sprint 7)
# ════════════════════════════════════════════════════════════════════

class SocioIn(BaseModel):
    nombre: str
    apellido: Optional[str] = None
    cuit: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    participacion_pct: Optional[float] = None
    activo: bool = True
    notas: Optional[str] = None
    user_id: Optional[int] = None  # vínculo opcional a un User


class SocioOut(SocioIn):
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
    # Sprint 21
    legalidad: LegalidadMovimiento = LegalidadMovimiento.blanco
    cobro_pago_estado: CobroPagoEstado = CobroPagoEstado.pendiente
    fecha_cobro_pago: Optional[date] = None
    iva_pct: Optional[float] = None
    iibb_pct: Optional[float] = None
    gastos_banco: float = 0


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
    # Sprint 21
    legalidad: LegalidadMovimiento = LegalidadMovimiento.blanco
    cobro_pago_estado: CobroPagoEstado = CobroPagoEstado.pendiente
    fecha_cobro_pago: Optional[date] = None
    iva_pct: Optional[float] = None
    iibb_pct: Optional[float] = None
    gastos_banco: float = 0

    class Config:
        from_attributes = True


class FlujoCajaSemana(BaseModel):
    semana: date
    ingresos: float
    egresos: float
    saldo_semana: float
    saldo_acumulado: float


# ─── Sprint 21: resumen contable blanco/negro por obra ───────────────────


class FinanzasCajaResumen(BaseModel):
    """Una caja (blanca o negra) desglosada por estado."""
    ingresos_cobrado: float = 0
    ingresos_pendiente: float = 0
    egresos_pagado: float = 0
    egresos_pendiente: float = 0
    iva_total: float = 0       # solo aplica caja blanco
    iibb_total: float = 0
    gastos_banco_total: float = 0
    neto_efectivo: float = 0   # cobrado - pagado (lo que tenés ya en mano)
    saldo_compromiso: float = 0  # cobrado_pendiente - pagado_pendiente (lo que va a entrar/salir)


class FinanzasObraResumen(BaseModel):
    """Resumen contable de una obra con desglose por caja blanco/negro.

    'lo que tenés' = neto_efectivo de las 2 cajas.
    'lo que se debe' = saldo_compromiso (positivo a favor, negativo en contra).
    """
    obra_id: int
    monto_contrato: float = 0
    blanco: FinanzasCajaResumen
    negro: FinanzasCajaResumen
    # Consolidado
    lo_que_tenes: float = 0
    lo_que_se_debe: float = 0   # neto: positivo = a favor, negativo = a pagar
    saldo_total: float = 0      # lo_que_tenes + lo_que_se_debe


class FinanzasMovimientoUpdate(BaseModel):
    """Patch parcial — usado por endpoints como marcar-cobrado/marcar-pagado."""
    cobro_pago_estado: Optional[CobroPagoEstado] = None
    fecha_cobro_pago: Optional[date] = None
    legalidad: Optional[LegalidadMovimiento] = None
    iva_pct: Optional[float] = None
    iibb_pct: Optional[float] = None
    gastos_banco: Optional[float] = None


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


# ─── Sprint 9: Stock multi-ubicación ───────────────────────────────────────

class StockUbicacionOut(BaseModel):
    """Una fila de stock_material con referencias resueltas."""
    stock_material_id: Optional[int] = None  # Sprint 14: id de la fila para acciones
    ubicacion_tipo: str  # 'deposito_propio' | 'en_obra' | 'comprado_no_retirado'
    ubicacion_ref: Optional[int] = None
    ubicacion_nombre: Optional[str] = None  # nombre de la obra o del proveedor (resuelto)
    cantidad: float
    fecha_retirar: Optional[date] = None  # Sprint 14: solo aplica si tipo=comprado_no_retirado

    class Config:
        from_attributes = True


class MaterialConStockOut(MaterialOut):
    """Material con desglose de stock por ubicación."""
    stock_total_disponible: float = 0      # deposito + en_obras
    stock_pendiente_retiro: float = 0      # comprado_no_retirado
    ubicaciones: List[StockUbicacionOut] = []


class StockMovimientoIn(BaseModel):
    """Payload genérico para movimientos de stock (operaciones del agente)."""
    material_id: int
    cantidad: float
    nota: Optional[str] = None


class StockCompraPendienteIn(StockMovimientoIn):
    proveedor_id: int


class StockRetiroProveedorIn(StockMovimientoIn):
    proveedor_id: int
    destino_tipo: str  # 'deposito_propio' | 'en_obra'
    destino_obra_id: Optional[int] = None  # requerido si destino_tipo == 'en_obra'


class StockConsumoIn(StockMovimientoIn):
    obra_id: int


class StockTransferenciaIn(StockMovimientoIn):
    origen_tipo: str   # 'deposito_propio' | 'en_obra'
    origen_obra_id: Optional[int] = None
    destino_tipo: str  # 'deposito_propio' | 'en_obra'
    destino_obra_id: Optional[int] = None


# ─── Sprint 14: Pedidos / retiros ──────────────────────────────────────────


class StockAgendarRetiroIn(BaseModel):
    fecha_retirar: date


class StockMarcarRetiradoIn(BaseModel):
    cantidad: float = Field(gt=0)
    fecha_retiro: Optional[date] = None  # default hoy
    forma_pago: Optional[MedioPago] = None
    en_negro: bool = False
    comprobante_id: Optional[int] = None
    destino_tipo: str = "deposito_propio"  # 'deposito_propio' | 'en_obra'
    destino_obra_id: Optional[int] = None
    notas: Optional[str] = None


class RetiroMaterialOut(BaseModel):
    id: int
    material_id: int
    proveedor_id: Optional[int] = None
    obra_destino_id: Optional[int] = None
    cantidad: float
    fecha_retiro: date
    forma_pago: Optional[MedioPago] = None
    en_negro: bool
    comprobante_id: Optional[int] = None
    notas: Optional[str] = None
    created_by_id: Optional[int] = None
    created_at: datetime
    # Campos resueltos para el frontend (opcional)
    material_nombre: Optional[str] = None
    proveedor_nombre: Optional[str] = None
    obra_destino_nombre: Optional[str] = None

    class Config:
        from_attributes = True


class StockPendienteRetiroOut(BaseModel):
    """Una fila de stock pendiente de retiro con datos resueltos."""
    stock_material_id: int
    material_id: int
    material_nombre: str
    unidad: str
    proveedor_id: Optional[int] = None
    proveedor_nombre: Optional[str] = None
    cantidad: float
    fecha_retirar: Optional[date] = None
    dias_para_retiro: Optional[int] = None  # None si no hay fecha
    alertado_at: Optional[datetime] = None


# ─── Sprint 10: Presupuestos ──────────────────────────────────────────────

class PresupuestoItemIn(BaseModel):
    material_id: int
    cantidad: float
    precio_unitario_estimado: Optional[float] = None  # si no se manda, toma el precio del Material


class PresupuestoItemOut(BaseModel):
    id: int
    material_id: int
    material_nombre: str
    cantidad: float
    precio_unitario_estimado: float
    subtotal: float

    class Config:
        from_attributes = True


class PresupuestoIn(BaseModel):
    obra_id: int
    nombre: str
    items: List[PresupuestoItemIn] = []
    notas: Optional[str] = None


class PresupuestoOut(BaseModel):
    id: int
    obra_id: int
    obra_nombre: str
    nombre: str
    estado: str
    total_estimado: float
    notas: Optional[str]
    created_at: datetime
    aprobado_at: Optional[datetime]
    items: List[PresupuestoItemOut]

    class Config:
        from_attributes = True


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


# ─── Sprint 15: detalle del proveedor (materiales que vende + historial) ────


class ProveedorMaterialOut(BaseModel):
    """Material que un proveedor vende (resuelto desde Material.proveedor_id)."""
    material_id: int
    nombre: str
    categoria: Optional[str] = None
    unidad: str
    precio_unitario: float
    stock_actual: float = 0  # sum(deposito + en_obras)
    pendiente_retiro: float = 0  # comprado_no_retirado para este proveedor


class ProveedorHistorialItem(BaseModel):
    """Item del historial del proveedor: una compra retirada (facturado) o un item
    en un presupuesto (presupuestado).
    """
    fecha: date
    tipo: str  # 'facturado' | 'presupuestado'
    material_id: int
    material_nombre: str
    unidad: str
    cantidad: float
    precio_unitario: Optional[float] = None
    subtotal: Optional[float] = None
    en_negro: Optional[bool] = None  # solo aplica a facturado
    forma_pago: Optional[MedioPago] = None  # solo facturado
    obra_destino_nombre: Optional[str] = None  # solo facturado, si fue directo a obra
    presupuesto_nombre: Optional[str] = None  # solo presupuestado
    presupuesto_estado: Optional[str] = None  # solo presupuestado
    ref_id: int  # id del RetiroMaterial o PresupuestoItem


class ProveedorDetalleOut(ProveedorOut):
    materiales_vendidos: List[ProveedorMaterialOut] = []
    ultima_actividad: Optional[date] = None  # max(fecha facturado/presupuestado)


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


# ════════════════════════════════════════════════════════════════════
# REQUERIMIENTOS POR OBRA (Sprint 17)
# ════════════════════════════════════════════════════════════════════

class RequerimientoIn(BaseModel):
    obra_id: int
    mensaje: str = Field(min_length=1, max_length=2000)


class RequerimientoOut(BaseModel):
    id: int
    obra_id: int
    mensaje: str
    estado: RequerimientoEstado
    canal: CanalCarga
    created_by_id: Optional[int] = None
    resuelto_by_id: Optional[int] = None
    created_at: datetime
    resuelto_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ════════════════════════════════════════════════════════════════════
# PERMISOS GRANULARES (Sprint 13)
# ════════════════════════════════════════════════════════════════════

class PermisosIn(BaseModel):
    """Payload PUT: lista de secciones permitidas + obras visibles.

    - secciones_permitidas: lista de slugs de secciones que el user puede ver.
      Cualquier seccion del catalogo (models.SECCIONES) que NO este aca se
      bloquea via fila allowed=False. Mandar None deja el estado actual.
    - obras_visibles_ids: whitelist de obra_ids. None = ve todas. Lista vacia = no ve ninguna.
    """
    secciones_permitidas: Optional[List[str]] = None
    obras_visibles_ids: Optional[List[int]] = None


class PermisosOut(BaseModel):
    user_id: int
    secciones_permitidas: List[str]
    secciones_bloqueadas: List[str]
    obras_visibles_ids: Optional[List[int]]  # None = ve todas
    secciones_catalogo: List[str]


# ════════════════════════════════════════════════════════════════════
# PLANIFICACION DE OBRA ASISTIDA (Sprint 24)
# ════════════════════════════════════════════════════════════════════


class PlanObraGenerarIn(BaseModel):
    model_config = ConfigDict(protected_namespaces=())  # permitir campo model_override
    contexto: str = Field(min_length=10, max_length=4000)
    model_override: Optional[str] = None


class PlanObraEtapaPropuesta(BaseModel):
    nombre: str
    nro_etapa: int = 0
    monto_contractual: float = 0
    porcentaje_avance: float = 0
    fecha_estimada: Optional[date] = None
    notas: Optional[str] = None


class PlanObraFrentePropuesto(BaseModel):
    nombre: str
    tipo: Optional[str] = None
    notas: Optional[str] = None


class PlanObraMaterialSugerido(BaseModel):
    nombre: str
    categoria: Optional[str] = None
    unidad: str = "u"
    cantidad: float = 0
    etapa: Optional[str] = None


class PlanObraResultado(BaseModel):
    etapas: List[PlanObraEtapaPropuesta] = []
    frentes: List[PlanObraFrentePropuesto] = []
    materiales_sugeridos: List[PlanObraMaterialSugerido] = []
    notas_generales: Optional[str] = None


class PlanObraBorradorOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    id: int
    obra_id: int
    prompt_input: str
    resultado: PlanObraResultado  # resultado_json deserializado
    estado: PlanObraEstado
    model_used: Optional[str] = None
    created_by_id: Optional[int] = None
    created_at: datetime
    aplicado_at: Optional[datetime] = None


class PlanObraEditIn(BaseModel):
    """Para editar el resultado del borrador antes de aplicarlo."""
    resultado: PlanObraResultado


class PlanObraAplicarOut(BaseModel):
    etapas_creadas: int
    frentes_creados: int
    materiales_sugeridos_count: int


# ════════════════════════════════════════════════════════════════════
# CONSOLIDACIÓN BANCARIA (Sprint 23)
# ════════════════════════════════════════════════════════════════════


class MovimientoBancarioIn(BaseModel):
    fecha: date
    descripcion: str = Field(min_length=1, max_length=500)
    debito: float = 0
    credito: float = 0
    saldo: Optional[float] = None


class ExtractoIn(BaseModel):
    banco: str = Field(min_length=1, max_length=100)
    cuenta: Optional[str] = Field(default=None, max_length=60)
    periodo_desde: Optional[date] = None
    periodo_hasta: Optional[date] = None
    archivo_nombre: Optional[str] = None
    movimientos: List[MovimientoBancarioIn] = Field(default_factory=list)


class MovimientoBancarioOut(BaseModel):
    id: int
    extracto_id: int
    fecha: date
    descripcion: str
    debito: float
    credito: float
    saldo: Optional[float] = None
    movimiento_obra_id: Optional[int] = None
    conciliado_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExtractoOut(BaseModel):
    id: int
    banco: str
    cuenta: Optional[str] = None
    periodo_desde: Optional[date] = None
    periodo_hasta: Optional[date] = None
    archivo_nombre: Optional[str] = None
    total_debe: float = 0
    total_haber: float = 0
    total_movs: int = 0
    created_by_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ExtractoDetalleOut(ExtractoOut):
    movimientos: List[MovimientoBancarioOut] = []


class MatchIn(BaseModel):
    movimiento_obra_id: int


class SugerenciaMatchOut(BaseModel):
    movimiento_obra_id: int
    obra_codigo: str
    concepto: str
    fecha: date
    monto: float
    tipo: TipoMovimiento
    distancia_dias: int  # |fecha_mov_obra - fecha_mov_bancario|


class MovimientoBancarioConSugerenciasOut(MovimientoBancarioOut):
    sugerencias: List[SugerenciaMatchOut] = []


class ConsolidacionResumen(BaseModel):
    extracto_id: int
    total_debe_extracto: float
    total_haber_extracto: float
    total_debe_obra_conciliado: float   # sum(monto) de EGRESO matcheados
    total_haber_obra_conciliado: float  # sum(monto) de INGRESO matcheados
    diferencia_debe: float   # total_debe_extracto - total_debe_obra_conciliado
    diferencia_haber: float
    movs_total: int
    movs_conciliados: int
    movs_sin_match: int


# ════════════════════════════════════════════════════════════════════
# OCR DE TICKETS (Sprint 18)
# ════════════════════════════════════════════════════════════════════


class TicketOCRItem(BaseModel):
    descripcion: Optional[str] = None
    cantidad: Optional[float] = None
    unidad: Optional[str] = None
    precio_unitario: Optional[float] = None
    subtotal: Optional[float] = None


class TicketOCRResultado(BaseModel):
    """Estructura del JSON devuelto por Claude Vision (todos opcionales — el
    LLM puede no detectar algunos campos)."""
    tipo_documento: Optional[str] = None
    nro_comprobante: Optional[str] = None
    punto_venta: Optional[int] = None
    fecha_emision: Optional[date] = None
    proveedor_nombre: Optional[str] = None
    proveedor_cuit: Optional[str] = None
    items: List[TicketOCRItem] = []
    neto_gravado: Optional[float] = None
    iva_21: Optional[float] = None
    iva_105: Optional[float] = None
    total: Optional[float] = None
    notas: Optional[str] = None


class TicketOCRSubirIn(BaseModel):
    """Subir un ticket desde la web — toma URL o base64 + datos de Telegram opcionales."""
    model_config = ConfigDict(protected_namespaces=())
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_message_id: Optional[str] = None
    telegram_file_id: Optional[str] = None
    model_override: Optional[str] = None


class TicketOCROut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    id: int
    estado: TicketOCREstado
    resultado: TicketOCRResultado
    model_used: Optional[str] = None
    error_msg: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    imagen_url_cached: Optional[str] = None
    obra_id: Optional[int] = None
    comprobante_id: Optional[int] = None
    movimiento_obra_id: Optional[int] = None
    created_by_id: Optional[int] = None
    created_at: datetime
    confirmed_at: Optional[datetime] = None


class TicketOCRConfirmarIn(BaseModel):
    """Datos para confirmar el ticket y crear Comprobante + Movimiento."""
    obra_id: int
    proveedor_id: Optional[int] = None  # si null, intenta match automático
    es_venta: bool = False  # default: comprobante recibido (egreso)
    categoria_egreso: Optional[CategoriaEgreso] = CategoriaEgreso.MATERIALES
    legalidad: LegalidadMovimiento = LegalidadMovimiento.blanco
    medio_pago: MedioPago = MedioPago.TRANSFERENCIA
    cobro_pago_estado: CobroPagoEstado = CobroPagoEstado.pendiente
    notas_extra: Optional[str] = None
