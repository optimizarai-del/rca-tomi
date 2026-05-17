"""Tests Sprint 11 — Bot de Telegram.

Cubre:
- Adaptador telegram_sender: log_only fallback, dedupe, persistencia.
- Webhook: bad secret, whitelist (policy b ignora silencioso), vinculación, slash, agente.
- Vinculación: endpoint admin genera código, /vincular asocia chat, código expirado falla.
"""
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from app import models
from app.messaging.telegram_sender import send_telegram, authorized_chat_ids


# ─── Adaptador ─────────────────────────────────────────────────────────────

def test_telegram_sender_log_only_si_falta_token(db, admin_user, monkeypatch):
    """Sin TELEGRAM_BOT_TOKEN, queda log_only sin intentar enviar."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    msg = send_telegram(db, chat_id="111", mensaje="hola")
    assert msg is not None
    assert msg.canal == "telegram"
    assert msg.status == models.OutboundMessageStatus.log_only
    assert msg.provider == "log_only"


def test_telegram_sender_dedupe(db, admin_user, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    a = send_telegram(db, "111", "alerta cheque vto 23/05", dedupe=True, context_key="cheque:42")
    b = send_telegram(db, "111", "alerta cheque vto 23/05", dedupe=True, context_key="cheque:42")
    assert a is not None
    assert b is None  # dedupeado


def test_telegram_sender_real_call(db, admin_user, monkeypatch):
    """Con token seteado, llama a la API; mockeamos httpx.post."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token-12345")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ok": True, "result": {"message_id": 999}}
    mock_resp.raise_for_status = MagicMock()

    with patch("app.messaging.telegram_sender.httpx.post", return_value=mock_resp) as mp:
        msg = send_telegram(db, "555", "hola Tomi")
    assert msg.status == models.OutboundMessageStatus.sent
    assert msg.provider == "telegram"
    assert msg.provider_message_id == "999"
    # verificar payload
    call_kwargs = mp.call_args.kwargs
    assert call_kwargs["json"]["chat_id"] == "555"
    assert call_kwargs["json"]["text"] == "hola Tomi"


def test_authorized_chat_ids_parsea_csv(monkeypatch):
    monkeypatch.setenv("TELEGRAM_AUTHORIZED_CHAT_IDS", "111, 222,333")
    assert authorized_chat_ids() == {"111", "222", "333"}
    monkeypatch.setenv("TELEGRAM_AUTHORIZED_CHAT_IDS", "")
    assert authorized_chat_ids() == set()


# ─── Webhook bad secret ────────────────────────────────────────────────────

def test_webhook_rechaza_secret_invalido(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "expected-secret")
    r = client.post("/api/telegram/webhook",
                    json={"message": {"chat": {"id": 1}, "text": "hi"}},
                    headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"})
    # devolvemos 200 con ok=False para no exponer info
    assert r.status_code == 200
    assert r.json()["ok"] is False


def test_webhook_acepta_secret_correcto(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "expected-secret")
    monkeypatch.setenv("TELEGRAM_AUTHORIZED_CHAT_IDS", "")  # vacía: nada autorizado
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    # chat_id no whitelisted + no es /vincular → silencio (policy b)
    r = client.post("/api/telegram/webhook",
                    json={"message": {"chat": {"id": 999}, "text": "hola"}},
                    headers={"X-Telegram-Bot-Api-Secret-Token": "expected-secret"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["handled"] is False
    assert body["reason"] == "not-whitelisted"


# ─── Vinculación end-to-end ────────────────────────────────────────────────

def test_admin_genera_codigo_y_user_vincula(client, db, admin_user, auth_headers, monkeypatch):
    """Admin genera código → /vincular asocia chat_id → User tiene telegram_chat_id."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)

    # 1. Admin pide un código para sí mismo
    r = client.post(f"/api/users/{admin_user.id}/telegram/generate-code", headers=auth_headers)
    assert r.status_code == 200
    code = r.json()["code"]
    assert len(code) == 6

    # 2. Verificamos que el código quedó en DB
    db.refresh(admin_user)
    assert admin_user.telegram_vinculacion_code == code
    assert admin_user.telegram_vinculacion_exp > datetime.utcnow()

    # 3. El user manda /vincular <code> desde Telegram
    r = client.post("/api/telegram/webhook",
                    json={"message": {
                        "chat": {"id": 7777},
                        "from": {"username": "tomi_test"},
                        "text": f"/vincular {code}",
                    }})
    assert r.status_code == 200
    body = r.json()
    assert body["handled"] is True
    assert body["mode"] == "vincular_ok"
    assert body["user_id"] == admin_user.id

    # 4. Verificamos que User quedó vinculado
    db.refresh(admin_user)
    assert admin_user.telegram_chat_id == "7777"
    assert admin_user.telegram_username == "tomi_test"
    assert admin_user.telegram_vinculacion_code is None  # se consume


def test_vincular_codigo_expirado_falla(client, db, admin_user, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
    # Seteo manual: código que ya expiró
    admin_user.telegram_vinculacion_code = "123456"
    admin_user.telegram_vinculacion_exp = datetime.utcnow() - timedelta(minutes=1)
    db.commit()

    r = client.post("/api/telegram/webhook",
                    json={"message": {"chat": {"id": 8888}, "text": "/vincular 123456"}})
    body = r.json()
    assert body["mode"] == "vincular_fail"
    db.refresh(admin_user)
    assert admin_user.telegram_chat_id is None


def test_vincular_codigo_inexistente_falla(client, db, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
    r = client.post("/api/telegram/webhook",
                    json={"message": {"chat": {"id": 9999}, "text": "/vincular 000000"}})
    body = r.json()
    assert body["mode"] == "vincular_fail"


def test_start_sin_codigo_da_instrucciones(client, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
    r = client.post("/api/telegram/webhook",
                    json={"message": {"chat": {"id": 1234}, "text": "/start"}})
    body = r.json()
    assert body["mode"] == "vincular_help"


# ─── Flujo agente / slash desde Telegram ──────────────────────────────────

def test_slash_desde_telegram_funciona(client, db, admin_user, monkeypatch):
    """Usuario vinculado y autorizado → /saldo responde con saldo global."""
    admin_user.telegram_chat_id = "5555"
    db.commit()
    monkeypatch.setenv("TELEGRAM_AUTHORIZED_CHAT_IDS", "5555")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)

    r = client.post("/api/telegram/webhook",
                    json={"message": {"chat": {"id": 5555}, "text": "/saldo"}})
    body = r.json()
    assert body["handled"] is True
    assert body["mode"] == "slash"


def test_chat_no_autorizado_es_ignorado_silencioso(client, db, admin_user, monkeypatch):
    """Policy (b): si no estás en whitelist y no es /vincular, ignorar silencioso."""
    monkeypatch.setenv("TELEGRAM_AUTHORIZED_CHAT_IDS", "111,222")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)

    r = client.post("/api/telegram/webhook",
                    json={"message": {"chat": {"id": 999}, "text": "hola bot"}})
    body = r.json()
    assert body["ok"] is True
    assert body["handled"] is False
    assert body["reason"] == "not-whitelisted"

    # Verificamos que NO se persistió ningún OutboundMessage hacia 999
    sent = db.query(models.OutboundMessage).filter(
        models.OutboundMessage.destinatario == "999"
    ).count()
    assert sent == 0


# ─── Desvincular ───────────────────────────────────────────────────────────

def test_admin_puede_desvincular_telegram(client, db, admin_user, auth_headers):
    admin_user.telegram_chat_id = "5555"
    admin_user.telegram_username = "tomi"
    db.commit()

    r = client.delete(f"/api/users/{admin_user.id}/telegram", headers=auth_headers)
    assert r.status_code == 204
    db.refresh(admin_user)
    assert admin_user.telegram_chat_id is None
    assert admin_user.telegram_username is None
