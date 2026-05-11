"""Password hashing + JWT."""
import pytest
from app.security import hash_password, verify_password, create_access_token
from jose import jwt
import os


def test_hash_password_returns_distinct_hash_each_time():
    h1 = hash_password("hola1234")
    h2 = hash_password("hola1234")
    assert h1 != h2  # bcrypt salt
    assert h1.startswith("$2") and len(h1) > 30


def test_verify_password_ok_and_fail():
    h = hash_password("secreto")
    assert verify_password("secreto", h) is True
    assert verify_password("otra", h) is False


def test_create_access_token_roundtrip():
    token = create_access_token({"sub": "42", "role": "admin"})
    decoded = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])
    assert decoded["sub"] == "42"
    assert decoded["role"] == "admin"
    assert "exp" in decoded
