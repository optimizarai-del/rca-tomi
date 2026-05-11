"""Magic links firmados (Sprint 4 · T5)."""
from app.approval import make_approval_token, verify_approval_token, approval_url


def test_make_and_verify_roundtrip():
    tok = make_approval_token(action_id=42, user_id=1, ttl_hours=1)
    payload = verify_approval_token(tok, action_id=42)
    assert payload is not None
    assert payload["confirmer"] == 1
    assert str(payload["sub"]) == "42"
    assert payload["aud"] == "approve"


def test_verify_con_action_id_distinto_falla():
    tok = make_approval_token(action_id=42, user_id=1)
    assert verify_approval_token(tok, action_id=99) is None


def test_verify_token_corrupto():
    tok = make_approval_token(action_id=42, user_id=1)
    assert verify_approval_token(tok + "xxx", action_id=42) is None
    assert verify_approval_token("totally.fake.token", action_id=42) is None


def test_approval_url_formato():
    tok = make_approval_token(action_id=42, user_id=1)
    url = approval_url("https://app.rca.com", 42, tok, confirm=True)
    assert url.startswith("https://app.rca.com/api/approve/42")
    assert "confirm=true" in url
    assert tok in url
