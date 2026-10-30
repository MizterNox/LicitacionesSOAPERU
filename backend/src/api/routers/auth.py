"""
Router de Autenticación y Perfil de Usuario:
- Registro de nuevos usuarios con hash Argon2.
- Inicio de sesión con emisión de JWT y cookie httpOnly para refresh token.
- Renovación silenciosa de sesión (refresh) y cierre de sesión.
- Consulta del perfil de usuario autenticado.
- Rate limiting contra fuerza bruta en login y registro (HTTP 429).
"""

import re
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie
from pydantic import BaseModel, Field, ConfigDict, field_validator
from sqlalchemy import select

from config import settings
from database import AsyncSessionLocal
from models.user import UserModel
from core.security import (
    hash_password,
    verify_password,
    verify_dummy_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    login_rate_limiter,
    login_ip_rate_limiter,
    register_rate_limiter,
)
from api.deps import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"

# Validación de correo pragmática (RFC 5322 simplificado, sin dependencias externas)
_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)


def _utcnow_naive() -> datetime:
    """UTC actual sin tzinfo (las columnas DateTime de users son naive)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_email(value: str) -> str:
    email = (value or "").strip().lower()
    if len(email) > 254 or not _EMAIL_RE.match(email):
        raise ValueError("Formato de correo electrónico inválido.")
    return email


# =========================================================================
# ESQUEMAS PYDANTIC
# =========================================================================

class UserRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: str = Field(..., max_length=254, description="Correo electrónico del usuario")
    password: str = Field(..., max_length=128, description="Contraseña (mín. 8 caracteres, letras y números)")
    nombre: str = Field(..., min_length=2, max_length=150, description="Nombre completo o razón social")
    # Campo aceptado por compatibilidad, pero ignorado: el registro público siempre crea rol 'user'
    rol: Optional[str] = Field(default="user", description="Ignorado: siempre 'user'")

    @field_validator("email")
    @classmethod
    def _v_email(cls, v: str) -> str:
        return _normalize_email(v)

    @field_validator("password")
    @classmethod
    def _v_password(cls, v: str) -> str:
        if len(v) < settings.PASSWORD_MIN_LENGTH:
            raise ValueError(
                f"La contraseña debe tener al menos {settings.PASSWORD_MIN_LENGTH} caracteres."
            )
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("La contraseña debe combinar letras y números.")
        return v

    @field_validator("nombre")
    @classmethod
    def _v_nombre(cls, v: str) -> str:
        clean = re.sub(r"[<>\x00-\x1f]", "", v).strip()
        if len(clean) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres válidos.")
        return clean


class UserLoginRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: str = Field(..., max_length=254, description="Correo electrónico")
    password: str = Field(..., min_length=1, max_length=128, description="Contraseña")

    @field_validator("email")
    @classmethod
    def _v_email(cls, v: str) -> str:
        return (v or "").strip().lower()


class UserResponse(BaseModel):
    id: int
    email: str
    nombre: str
    rol: str
    activo: bool
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None


# =========================================================================
# UTILIDADES
# =========================================================================

def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _raise_too_many(retry_after: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f"Demasiados intentos. Intente nuevamente en {retry_after} segundos.",
        headers={"Retry-After": str(retry_after)},
    )


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        path=REFRESH_COOKIE_PATH,
    )


def _issue_tokens(user: UserModel, response: Response) -> str:
    user_data = {"sub": str(user.id), "email": user.email, "rol": user.rol}
    access_token = create_access_token(user_data)
    _set_refresh_cookie(response, create_refresh_token(user_data))
    response.headers["Cache-Control"] = "no-store"
    return access_token


# =========================================================================
# ENDPOINTS DE AUTENTICACIÓN
# =========================================================================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegisterRequest, request: Request, response: Response):
    """Registra una nueva cuenta de usuario en el sistema."""
    ip_key = f"register:{_client_ip(request)}"
    wait = register_rate_limiter.retry_after(ip_key)
    if wait:
        _raise_too_many(wait)
    # Cada intento de registro cuenta (exitoso o no) para frenar creación masiva de cuentas
    register_rate_limiter.hit(ip_key)

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(UserModel).where(UserModel.email == payload.email))
        if res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya se encuentra registrado."
            )

        now = _utcnow_naive()
        new_user = UserModel(
            email=payload.email,
            password_hash=hash_password(payload.password),
            nombre=payload.nombre,
            # Seguridad: registro público siempre asigna rol 'user' (previene escalación de privilegios)
            rol="user",
            activo=True,
            creado_en=now,
            actualizado_en=now,
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

        access_token = _issue_tokens(new_user, response)
        return TokenResponse(access_token=access_token, user=UserResponse.model_validate(new_user))


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLoginRequest, request: Request, response: Response):
    """Inicia sesión validando credenciales y emite access token y cookie httpOnly."""
    ip = _client_ip(request)
    ip_key = f"login-ip:{ip}"
    pair_key = f"login:{ip}:{payload.email}"

    # Bloqueo por par IP+email (fuerza bruta dirigida) y por IP (credential stuffing)
    wait = login_rate_limiter.retry_after(pair_key) or login_ip_rate_limiter.retry_after(ip_key)
    if wait:
        _raise_too_many(wait)

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(UserModel).where(UserModel.email == payload.email))
        user = res.scalar_one_or_none()

        if user is None:
            verify_dummy_password(payload.password)
            valid = False
        else:
            valid = verify_password(payload.password, user.password_hash)

        if not valid:
            login_rate_limiter.hit(pair_key)
            login_ip_rate_limiter.hit(ip_key)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Correo electrónico o contraseña incorrectos."
            )

        if not user.activo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La cuenta se encuentra desactivada. Contacte al administrador."
            )

        login_rate_limiter.reset(pair_key)
        access_token = _issue_tokens(user, response)
        return TokenResponse(access_token=access_token, user=UserResponse.model_validate(user))


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    payload: Optional[RefreshTokenRequest] = None,
    refresh_token_cookie: Optional[str] = Cookie(default=None, alias=REFRESH_COOKIE_NAME)
):
    """Renueva el token de acceso mediante el refresh token enviado en cookie o body (rotación)."""
    raw_token = (
        refresh_token_cookie
        or (payload.refresh_token if payload else None)
        or request.headers.get("x-refresh-token")
    )

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó un token de renovación (refresh token)."
        )

    decoded = decode_token(raw_token, expected_type="refresh")
    if not decoded:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de renovación inválido o expirado."
        )

    try:
        user_id = int(decoded.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de renovación inválido."
        )

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(UserModel).where(UserModel.id == user_id))
        user = res.scalar_one_or_none()

        if not user or not user.activo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no válido o desactivado."
            )

        new_access_token = _issue_tokens(user, response)
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "user": UserResponse.model_validate(user)
        }


@router.post("/logout")
async def logout(response: Response):
    """Cierra la sesión activa eliminando la cookie del refresh token."""
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
    )
    # Limpieza de cookie heredada (versiones previas la emitían en path '/')
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/")
    return {"message": "Sesión cerrada correctamente."}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserModel = Depends(get_current_user)):
    """Retorna la información del perfil del usuario actualmente autenticado."""
    return current_user
