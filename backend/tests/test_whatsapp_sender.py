"""Adapter saliente — modo log_only sin tocar la red."""
from app import models
from app.whatsapp_sender import send_whatsapp, normalize_phone


def test_normalize_phone():
    assert normalize_phone("+5491100000001") == "+5491100000001"
    assert normalize_phone("whatsapp:+5491100000001") == "+5491100000001"
    assert normalize_phone("+54 911 0000-0001") == "+5491100000001"
    assert normalize_phone("") == ""


def test_send_log_only_persiste(db, admin_user):
    m = send_whatsapp(db, "+5491100001234", "hola test", user_id=admin_user.id, notification_type="manual")
    assert m.status == models.OutboundMessageStatus.log_only
    assert m.destinatario == "+5491100001234"
    assert m.provider == "log_only"
    assert m.sent_at is not None
    assert m.user_id == admin_user.id


def test_dedupe_no_duplica(db, admin_user):
    m1 = send_whatsapp(db, "+5491100001234", "hola", user_id=admin_user.id,
                       context_key="test_dedupe_1", dedupe=True)
    m2 = send_whatsapp(db, "+5491100001234", "hola", user_id=admin_user.id,
                       context_key="test_dedupe_1", dedupe=True)
    assert m1 is not None
    assert m2 is None  # dedupe lo saltó


def test_dedupe_distinto_context_key_si_envia(db, admin_user):
    m1 = send_whatsapp(db, "+5491100001234", "hola", user_id=admin_user.id,
                       context_key="key_a", dedupe=True)
    m2 = send_whatsapp(db, "+5491100001234", "hola", user_id=admin_user.id,
                       context_key="key_b", dedupe=True)
    assert m1 is not None
    assert m2 is not None


def test_provider_desconocido_failed(db, admin_user, monkeypatch):
    monkeypatch.setenv("WHATSAPP_PROVIDER", "marciano")
    m = send_whatsapp(db, "+5491100001234", "x", user_id=admin_user.id)
    assert m.status == models.OutboundMessageStatus.failed
    assert "marciano" in (m.error or "")
