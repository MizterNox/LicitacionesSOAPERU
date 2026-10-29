"""
Dependencias de inyección para FastAPI:
- Autenticación mediante Bearer Token JWT.
- Control de acceso por roles (RBAC: 'user' y 'admin').
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select

from database import AsyncSessionLocal
from models.user import UserModel
from core.security import decode_token

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> UserModel:
    """
    Obtiene y valida el usuario actual autenticado a partir del header Authorization Bearer
    o de la cookie de sesión.
    """
    token = None
    if credentials:
        token = credentials.credentials
    elif request:
        auth_hdr = request.headers.get("Authorization")
        if auth_hdr and auth_hdr.startswith("Bearer "):
            token = auth_hdr.split(" ")[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida. Inicie sesión para continuar.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no contiene identificador de usuario válido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async with AsyncSessionLocal() as session:
        try:
            uid_int = int(user_id)
            res = await session.execute(select(UserModel).where(UserModel.id == uid_int))
        except ValueError:
            res = await session.execute(select(UserModel).where(UserModel.email == str(user_id)))

        user = res.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado en la base de datos.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.activo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La cuenta de usuario se encuentra desactivada.",
            )

        return user


async def get_current_active_admin(
    current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    """Verifica que el usuario autenticado cuente con privilegios de administrador ('admin')."""
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: Se requieren privilegios de Administrador para esta operación.",
        )
    return current_user


async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Optional[UserModel]:
    """Retorna el usuario si el token es válido, o None si no hay sesión activa."""
    try:
        return await get_current_user(request=request, credentials=credentials)
    except HTTPException:
        return None
