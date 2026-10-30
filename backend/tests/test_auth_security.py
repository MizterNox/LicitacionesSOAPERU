"""
Suite de verificación de seguridad del módulo de autenticación (Fase 1 - Auditoría OWASP).

Comprueba que la API:
1. Rechaza credenciales inválidas (401) sin revelar si el usuario existe.
2. Rechaza tokens manipulados, expirados, sin firma válida o de tipo incorrecto (401).
3. Bloquea accesos no autorizados a rutas protegidas y endpoints administrativos (401).
4. Aplica rate limiting contra fuerza bruta (429 + Retry-After).
5. Aplica validación estricta de entrada (422) y CORS sin comodín.
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app
from config import settings
from core.security import (
    AuthRateLimiter,
    create_access_token,
    create_refresh_token,
    decode_token,
)

PASSWORD = "SoaPeru2026Seguro"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _register_and_login(ac: AsyncClient):
    email = f"sec_{uuid.uuid4().hex[:10]}@soaperu.pe"
    res = await ac.post("/api/v1/auth/register", json={
        "email": email, "password": PASSWORD, "nombre": "Auditor Seguridad"
    })
    assert res.status_code == 201, res.text
    return email, res.json()["access_token"], res.cookies.get("refresh_token")


# =========================================================================
# 1. CREDENCIALES INVÁLIDAS
# =========================================================================

@pytest.mark.asyncio
async def test_login_rechaza_credenciales_invalidas():
    async with _client() as ac:
        email, _, _ = await _register_and_login(ac)

        res_bad_pwd = await ac.post("/api/v1/auth/login", json={"email": email, "password": "Incorrecta999"})
        assert res_bad_pwd.status_code == 401

        res_no_user = await ac.post("/api/v1/auth/login", json={
            "email": "no_existe_xyz@soaperu.pe", "password": "Incorrecta999"
        })
        assert res_no_user.status_code == 401
        # Mismo mensaje: no se filtra la existencia de la cuenta
        assert res_bad_pwd.json()["detail"] == res_no_user.json()["detail"]

        res_ok = await ac.post("/api/v1/auth/login", json={"email": email.upper(), "password": PASSWORD})
        assert res_ok.status_code == 200
        assert res_ok.headers.get("cache-control") == "no-store"
        set_cookie = res_ok.headers.get("set-cookie", "").lower()
        assert "httponly" in set_cookie
        assert "path=/api/v1/auth" in set_cookie


@pytest.mark.asyncio
async def test_registro_ignora_rol_admin_enviado_por_cliente():
    async with _client() as ac:
        email = f"esc_{uuid.uuid4().hex[:10]}@soaperu.pe"
        res = await ac.post("/api/v1/auth/register", json={
            "email": email, "password": PASSWORD, "nombre": "Intento Escalada", "rol": "admin"
        })
        assert res.status_code == 201
        assert res.json()["user"]["rol"] == "user"


# =========================================================================
# 2. TOKENS MANIPULADOS / EXPIRADOS / TIPO INCORRECTO
# =========================================================================

@pytest.mark.asyncio
async def test_rechaza_tokens_manipulados():
    async with _client() as ac:
        _, access, refresh = await _register_and_login(ac)

        # Token válido funciona
        assert (await ac.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})).status_code == 200

        # a) Firma alterada
        head, body, sig = access.split(".")
        tampered_sig = f"{head}.{body}.{sig[:-2]}{'AA' if sig[-2:] != 'AA' else 'BB'}"
        # b) Payload alterado (rol admin) conservando la firma original
        forged_payload = jwt.encode(
            {**jwt.decode(access, options={"verify_signature": False}), "rol": "admin"},
            "clave-falsa", algorithm="HS256"
        ).split(".")[1]
        tampered_body = f"{head}.{forged_payload}.{sig}"
        # c) Firmado con otro secreto
        other_secret = jwt.encode(
            {"sub": "1", "type": "access", "iat": datetime.now(timezone.utc),
             "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
            "secreto-del-atacante", algorithm="HS256"
        )
        # d) Algoritmo 'none'
        alg_none = jwt.encode(
            {"sub": "1", "type": "access", "iat": datetime.now(timezone.utc),
             "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
            None, algorithm="none"
        )
        # e) Expirado
        expired = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-10))
        # f) Refresh token usado como access token
        # g) Basura
        for bad in [tampered_sig, tampered_body, other_secret, alg_none, expired, refresh, "no.es.jwt", "x"]:
            res = await ac.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bad}"})
            assert res.status_code == 401, f"Token aceptado indebidamente: {bad[:25]}..."

        # Access token usado como refresh token -> 401 (sin cookie válida que lo respalde)
        ac.cookies.clear()
        res_ref = await ac.post("/api/v1/auth/refresh", json={"refresh_token": access})
        assert res_ref.status_code == 401


def test_decode_token_exige_claims_y_tipo():
    tok = create_refresh_token({"sub": "7"})
    assert decode_token(tok, expected_type="refresh")["sub"] == "7"
    assert decode_token(tok, expected_type="access") is None
    assert decode_token(tok)["jti"]  # identificador único presente

    sin_sub = jwt.encode(
        {"type": "access", "iat": datetime.now(timezone.utc),
         "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    assert decode_token(sin_sub) is None
    assert decode_token("") is None
    assert decode_token(None) is None  # type: ignore[arg-type]


# =========================================================================
# 3. ACCESOS NO AUTORIZADOS
# =========================================================================

@pytest.mark.asyncio
async def test_rutas_protegidas_exigen_autenticacion():
    async with _client() as ac:
        assert (await ac.get("/api/v1/auth/me")).status_code == 401
        assert (await ac.get("/api/v1/me/filters")).status_code == 401
        assert (await ac.post("/api/v1/etl/trigger", json={"objeto": "Servicios"})).status_code == 401
        assert (await ac.post("/api/v1/settings/tipos", json={"tipos_activos": ["Servicios"]})).status_code == 401
        assert (await ac.get("/api/v1/auth/me", headers={"Authorization": "Basic abc"})).status_code == 401


# =========================================================================
# 4. RATE LIMITING
# =========================================================================

@pytest.mark.asyncio
async def test_rate_limit_login_bloquea_fuerza_bruta():
    async with _client() as ac:
        email, _, _ = await _register_and_login(ac)
        limite = settings.AUTH_RATE_LIMIT_ATTEMPTS

        for _ in range(limite):
            res = await ac.post("/api/v1/auth/login", json={"email": email, "password": "Incorrecta999"})
            assert res.status_code == 401

        bloqueado = await ac.post("/api/v1/auth/login", json={"email": email, "password": "Incorrecta999"})
        assert bloqueado.status_code == 429
        assert int(bloqueado.headers["retry-after"]) > 0

        # Incluso con la contraseña correcta, sigue bloqueado durante la ventana
        bloqueado_ok = await ac.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
        assert bloqueado_ok.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_registro():
    async with _client() as ac:
        codes = []
        for _ in range(settings.AUTH_RATE_LIMIT_ATTEMPTS + 1):
            res = await ac.post("/api/v1/auth/register", json={
                "email": f"spam_{uuid.uuid4().hex[:8]}@soaperu.pe", "password": PASSWORD, "nombre": "Bot"
            })
            codes.append(res.status_code)
        assert codes[-1] == 429
        assert all(c == 201 for c in codes[:-1])


def test_rate_limiter_ventana_y_reset():
    rl = AuthRateLimiter(max_attempts=2, window_seconds=60)
    assert rl.retry_after("k") == 0
    rl.hit("k"); rl.hit("k")
    assert rl.retry_after("k") > 0
    rl.reset("k")
    assert rl.retry_after("k") == 0


# =========================================================================
# 5. VALIDACIÓN DE ENTRADA Y CORS
# =========================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"email": "sin-arroba.pe", "password": PASSWORD, "nombre": "X Y"},
    {"email": "a@b", "password": PASSWORD, "nombre": "X Y"},
    {"email": "ok@soaperu.pe", "password": "corta1", "nombre": "X Y"},
    {"email": "ok@soaperu.pe", "password": "soloLetrasLargas", "nombre": "X Y"},
    {"email": "ok@soaperu.pe", "password": PASSWORD, "nombre": "<"},
])
async def test_registro_validacion_estricta(payload):
    async with _client() as ac:
        res = await ac.post("/api/v1/auth/register", json=payload)
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_cors_rechaza_origen_no_autorizado():
    assert "*" not in settings.cors_origins_list
    async with _client() as ac:
        preflight_ok = await ac.options("/api/v1/auth/login", headers={
            "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"
        })
        assert preflight_ok.headers.get("access-control-allow-origin") == "http://localhost:5173"

        preflight_evil = await ac.options("/api/v1/auth/login", headers={
            "Origin": "https://sitio-malicioso.example", "Access-Control-Request-Method": "POST"
        })
        assert preflight_evil.headers.get("access-control-allow-origin") is None

        res = await ac.get("/api/v1/health")
        assert res.headers.get("x-content-type-options") == "nosniff"
