"""Parser de slash commands del WhatsApp. No requiere LLM."""
from datetime import date
from app import models
from app.slash_commands import is_slash_command, handle_slash, fmt_money


def test_is_slash_command():
    assert is_slash_command("/saldo")
    assert is_slash_command("  /cheques 60  ")
    assert is_slash_command("/help")
    assert not is_slash_command("hola")
    assert not is_slash_command("")
    assert not is_slash_command("saldo IDS")


def test_fmt_money_signo_correcto():
    assert fmt_money(1500000) == "$1.50M"
    assert fmt_money(-450000) == "-$450k"
    assert fmt_money(0) == "$0"
    assert fmt_money(999) == "$999"


def test_help_lista_comandos(db, admin_user):
    r = handle_slash("/help", admin_user, db)
    assert r["ok"]
    assert "/saldo" in r["reply"]
    assert "/cheques" in r["reply"]
    assert "/gasto" in r["reply"]


def test_saldo_global(db, admin_user, obra):
    r = handle_slash("/saldo", admin_user, db)
    assert r["ok"]
    assert "Saldo global" in r["reply"]
    assert r["saldo"] == 0  # sin movimientos


def test_saldo_por_obra(db, admin_user, obra):
    r = handle_slash(f"/saldo TST", admin_user, db)
    assert r["ok"]
    assert "TST" in r["reply"]
    assert r["obra_id"] == obra.id


def test_saldo_obra_inexistente_error(db, admin_user):
    r = handle_slash("/saldo XXX", admin_user, db)
    assert not r["ok"]
    assert "no encontrada" in r["reply"].lower()


def test_avance_actualiza_progreso_y_crea_evento(db, admin_user, obra):
    progreso_antes = obra.progreso
    r = handle_slash("/avance TST 65", admin_user, db)
    assert r["ok"]
    db.refresh(obra)
    assert abs(obra.progreso - 65) < 0.01

    evs = db.query(models.Evento).filter_by(obra_id=obra.id).all()
    assert len(evs) == 1
    assert evs[0].tipo == models.EventoTipo.avance
    assert evs[0].canal == models.CanalCarga.whatsapp


def test_avance_fuera_de_rango(db, admin_user, obra):
    r = handle_slash("/avance TST 200", admin_user, db)
    assert not r["ok"]
    r2 = handle_slash("/avance TST -5", admin_user, db)
    assert not r2["ok"]


def test_gasto_crea_movimiento_a_revisar(db, admin_user, obra):
    r = handle_slash("/gasto TST 5000 nafta camion", admin_user, db)
    assert r["ok"]
    m = db.query(models.MovimientoObra).filter_by(id=r["movimiento_id"]).first()
    assert m.tipo == models.TipoMovimiento.EGRESO
    assert m.categoria_egreso == models.CategoriaEgreso.GASTO_DIRECTO_OBRA
    assert m.estado == models.EstadoMovimiento.A_REVISAR
    assert m.canal == models.CanalCarga.whatsapp
    assert float(m.monto) == 5000
    assert m.concepto == "nafta camion"


def test_gasto_monto_invalido(db, admin_user, obra):
    r = handle_slash("/gasto TST abc nafta", admin_user, db)
    assert not r["ok"]
    assert "monto" in r["reply"].lower()


def test_comando_desconocido(db, admin_user):
    r = handle_slash("/inexistente", admin_user, db)
    assert not r["ok"]
    assert "desconocido" in r["reply"].lower()
