import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app
from core.security import hash_password, verify_password


def test_argon2_security():
    pwd = "SecretPassword2026!"
    hashed = hash_password(pwd)
    assert hashed.startswith("$argon2")
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False


@pytest.mark.asyncio
async def test_auth_full_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        test_email = "analista_test@licitlens.pe"
        test_pass = "PeruCompras2026!"

        # 1. Registro de usuario
        res_reg = await ac.post("/api/v1/auth/register", json={
            "email": test_email,
            "password": test_pass,
            "nombre": "Analista de Licitaciones",
            "rol": "user"
        })
        # Si ya existe por una corrida previa, no falla
        if res_reg.status_code == 201:
            data = res_reg.json()
            assert "access_token" in data
            assert data["user"]["email"] == test_email
            assert "refresh_token" in res_reg.cookies
        else:
            assert res_reg.status_code == 400

        # 2. Login con credenciales válidas
        res_login = await ac.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": test_pass
        })
        assert res_login.status_code == 200
        login_data = res_login.json()
        token = login_data["access_token"]
        assert token is not None

        # 3. Login con contraseña errónea
        res_bad = await ac.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": "WrongPassword123"
        })
        assert res_bad.status_code == 401

        # 4. Consulta de perfil /auth/me
        res_me = await ac.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res_me.status_code == 200
        me_data = res_me.json()
        assert me_data["email"] == test_email
        assert me_data["nombre"] == "Analista de Licitaciones"

        # 5. Consulta /auth/me sin token -> 401
        res_no_auth = await ac.get("/api/v1/auth/me")
        assert res_no_auth.status_code == 401

        # 6. Renovación silenciosa con refresh token en body
        refresh_cookie = res_login.cookies.get("refresh_token")
        res_refresh = await ac.post("/api/v1/auth/refresh", json={"refresh_token": refresh_cookie})
        assert res_refresh.status_code == 200
        assert "access_token" in res_refresh.json()

        # 7. Logout
        res_logout = await ac.post("/api/v1/auth/logout")
        assert res_logout.status_code == 200
