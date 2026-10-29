"""
Router de Autenticación y Perfil de Usuario:
- Registro de nuevos usuarios con hash Argon2.
- Inicio de sesión con emisión de JWT y cookie httpOnly para refresh token.
- Renovación silenciosa de sesión (refresh) y cierre de sesión.
- Consulta del perfil de usuario autenticado.
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from sqlalchemy import select

from database import AsyncSessionLocal
from models.user import UserModel
from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from api.deps import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])


# =========================================================================
# ESQUEMAS PYDANTIC
# =========================================================================

class UserRegisterRequest(BaseModel):
    email: str = Field(..., description="Correo electrónico del usuario")
    password: str = Field(..., min_length=6, description="Contraseña de al menos 6 caracteres")
    nombre: str = Field(..., min_length=2, description="Nombre completo o razón social")
    rol: Optional[str] = Field(default="user", description="'user' o 'admin'")


class UserLoginRequest(BaseModel):
    email: str = Field(..., description="Correo electrónico")
    password: str = Field(..., description="Contraseña")


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
# ENDPOINTS DE AUTENTICACIÓN
# =========================================================================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegisterRequest, response: Response):
    """Registra una nueva cuenta de usuario en el sistema."""
    clean_email = payload.email.strip().lower()
    if "@" not in clean_email or "." not in clean_email:
        raise HTTPException(status_code=400, detail="Formato de correo electrónico inválido.")

    async with AsyncSessionLocal() as session:
        # Verificar si el email ya existe
        res = await session.execute(select(UserModel).where(UserModel.email == clean_email))
        if res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya se encuentra registrado."
            )

        hashed = hash_password(payload.password)
        # Seguridad: registro público siempre asigna rol 'user' para prevenir escalación de privilegios
        user_rol = "user"

        new_user = UserModel(
            email=clean_email,
            password_hash=hashed,
            nombre=payload.nombre.strip(),
            rol=user_rol,
            activo=True,
            creado_en=datetime.utcnow(),
            actualizado_en=datetime.utcnow()
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

        user_data = {"sub": str(new_user.id), "email": new_user.email, "rol": new_user.rol}
        access_token = create_access_token(user_data)
        refresh_token = create_refresh_token(user_data)

        # Configurar cookie httpOnly para refresh token (7 días)
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            max_age=7 * 24 * 3600,
            samesite="lax",
            secure=False
        )

        return TokenResponse(
            access_token=access_token,
            user=UserResponse.model_validate(new_user)
        )


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLoginRequest, response: Response):
    """Inicia sesión validando credenciales y emite access token y cookie httpOnly."""
    clean_email = payload.email.strip().lower()

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(UserModel).where(UserModel.email == clean_email))
        user = res.scalar_one_or_none()

        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Correo electrónico o contraseña incorrectos."
            )

        if not user.activo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La cuenta se encuentra desactivada. Contacte al administrador."
            )

        user_data = {"sub": str(user.id), "email": user.email, "rol": user.rol}
        access_token = create_access_token(user_data)
        refresh_token = create_refresh_token(user_data)

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            max_age=7 * 24 * 3600,
            samesite="lax",
            secure=False
        )

        return TokenResponse(
            access_token=access_token,
            user=UserResponse.model_validate(user)
        )


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    payload: Optional[RefreshTokenRequest] = None,
    refresh_token_cookie: Optional[str] = Cookie(default=None, alias="refresh_token")
):
    """Renueva el token de acceso mediante el refresh token enviado en cookie o body."""
    raw_token = refresh_token_cookie or (payload.refresh_token if payload else None)

    if not raw_token:
        # Intentar leer desde cabeceras si no vino en cookie
        raw_token = request.headers.get("x-refresh-token")

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó un token de renovación (refresh token)."
        )

    decoded = decode_token(raw_token)
    if not decoded or decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de renovación inválido o expirado."
        )

    user_id = decoded.get("sub")
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(UserModel).where(UserModel.id == int(user_id)))
        user = res.scalar_one_or_none()

        if not user or not user.activo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no válido o desactivado."
            )

        user_data = {"sub": str(user.id), "email": user.email, "rol": user.rol}
        new_access_token = create_access_token(user_data)
        new_refresh_token = create_refresh_token(user_data)

        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            max_age=7 * 24 * 3600,
            samesite="lax",
            secure=False
        )

        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "user": UserResponse.model_validate(user)
        }


@router.post("/logout")
async def logout(response: Response):
    """Cierra la sesión activa eliminando la cookie del refresh token."""
    response.delete_cookie(key="refresh_token", httponly=True, samesite="lax")
    return {"message": "Sesión cerrada correctamente."}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserModel = Depends(get_current_user)):
    """Retorna la información del perfil del usuario actualmente autenticado."""
    return current_user
