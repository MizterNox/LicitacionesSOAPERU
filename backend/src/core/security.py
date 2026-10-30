"""
Módulo de seguridad criptográfica:
- Hashing de contraseñas con Argon2 (algoritmo ganador de Password Hashing Competition).
- Generación y validación de tokens JWT (Access Token de 30 min y Refresh Token de 7 días).
- Limitador de tasa (rate limiting) en memoria contra fuerza bruta en autenticación.
"""

import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Deque

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

from config import settings

_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MB
    parallelism=1,
    hash_len=32,
    salt_len=16
)

# Hash ficticio para igualar el tiempo de respuesta cuando el usuario no existe
# (mitiga enumeración de cuentas por análisis de tiempos).
_DUMMY_HASH = _hasher.hash("soaperu-dummy-password-timing-shield")


def hash_password(password: str) -> str:
    """Genera hash seguro Argon2 a partir de la contraseña en texto plano."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña en texto plano coincide con el hash Argon2."""
    if not hashed_password or not plain_password:
        return False
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False
    except Exception:
        return False


def verify_dummy_password(plain_password: str) -> None:
    """Ejecuta una verificación Argon2 descartable (tiempo constante ante usuario inexistente)."""
    verify_password(plain_password or "x", _DUMMY_HASH)


def _build_token(data: Dict[str, Any], token_type: str, expire: datetime) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "nbf": now,
        "jti": uuid.uuid4().hex,
        "type": token_type,
    })
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Crea un Access Token JWT firmado (vida útil por defecto: 30 minutos)."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return _build_token(data, "access", expire)


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Crea un Refresh Token JWT firmado (vida útil por defecto: 7 días)."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    return _build_token(data, "refresh", expire)


def decode_token(token: str, expected_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Decodifica y valida firma, expiración y claims obligatorios de un token JWT.
    - Fija el algoritmo permitido (evita ataques 'alg=none' / confusión de algoritmo).
    - Exige los claims exp, iat, sub y type.
    - Si se indica expected_type, rechaza tokens de otro tipo (ej. refresh usado como access).
    """
    if not token or not isinstance(token, str):
        return None
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub", "type"]},
        )
    except jwt.PyJWTError:
        return None

    if expected_type and payload.get("type") != expected_type:
        return None
    return payload


# =========================================================================
# RATE LIMITING (ventana deslizante en memoria, thread-safe)
# =========================================================================

class AuthRateLimiter:
    """
    Limitador de intentos por clave (IP, IP+email) con ventana deslizante.
    Adecuado para un despliegue de un solo proceso; para múltiples workers
    se recomienda migrar el almacenamiento a Redis.
    """

    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> Deque[float]:
        bucket = self._hits[key]
        limit = now - self.window_seconds
        while bucket and bucket[0] <= limit:
            bucket.popleft()
        return bucket

    def retry_after(self, key: str) -> int:
        """Segundos restantes de bloqueo para la clave (0 si no está bloqueada)."""
        now = time.monotonic()
        with self._lock:
            bucket = self._prune(key, now)
            if len(bucket) < self.max_attempts:
                if not bucket:
                    self._hits.pop(key, None)
                return 0
            return max(1, int(bucket[0] + self.window_seconds - now) + 1)

    def hit(self, key: str) -> None:
        """Registra un intento (fallido) para la clave."""
        now = time.monotonic()
        with self._lock:
            self._prune(key, now).append(now)

    def reset(self, key: Optional[str] = None) -> None:
        """Limpia los intentos de una clave (tras login exitoso) o de todas."""
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


login_rate_limiter = AuthRateLimiter(
    max_attempts=settings.AUTH_RATE_LIMIT_ATTEMPTS,
    window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
)

# Umbral global por IP (credential stuffing contra múltiples cuentas): 4x el límite por cuenta
login_ip_rate_limiter = AuthRateLimiter(
    max_attempts=settings.AUTH_RATE_LIMIT_ATTEMPTS * 4,
    window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
)

register_rate_limiter = AuthRateLimiter(
    max_attempts=settings.AUTH_RATE_LIMIT_ATTEMPTS,
    window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
)
