import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Configuración centralizada del proyecto usando Pydantic Settings.
    Carga variables desde el entorno o desde el archivo .env.
    """
    # Conexión a Base de Datos
    DATABASE_URL: str = "postgresql+asyncpg://postgres:admin26@localhost:5432/licitacionesELT"

    # API OECE (Contrataciones Abiertas de Perú)
    API_URL: str = "https://contratacionesabiertas.oece.gob.pe/api/v1/releases"

    # Parámetros de Negocio: Contrataciones Menores (Perú - UIT)
    UIT_VALOR_PEN: float = 5350.0
    TOPE_MENOR_CUANTIA_UIT: int = 8
    TOPE_MENOR_CUANTIA_PEN: float = 42800.0  # 8 UIT (5350 * 8)

    # Servidor Web FastAPI
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Configuración de Inteligencia Artificial (Google Gemini)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    AI_ENABLED: bool = True
    AI_BATCH_SIZE: int = 15
    AI_MAX_CONCURRENCY: int = 3

    # Seguridad y Autenticación JWT
    JWT_SECRET: str = "licitlens-secret-key-fase3-secure-token-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ADMIN_EMAIL: Optional[str] = None  # Usuario promovido a 'admin' automáticamente en el bootstrap

    # CORS: lista explícita de orígenes autorizados (separados por coma en .env).
    # Nunca usar "*" junto con allow_credentials=True (OWASP A05).
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:8080,http://127.0.0.1:8080"
    )

    # Cookie del refresh token: activar COOKIE_SECURE=true en producción (HTTPS)
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    # Rate limiting contra fuerza bruta en login / registro
    AUTH_RATE_LIMIT_ATTEMPTS: int = 5
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 60
    PASSWORD_MIN_LENGTH: int = 8

    @property
    def cors_origins_list(self) -> list[str]:
        """Orígenes CORS normalizados, descartando comodines inseguros."""
        return [
            o.strip().rstrip("/")
            for o in self.CORS_ORIGINS.split(",")
            if o.strip() and o.strip() != "*"
        ]

    # Configuración de Servidor de Correo (SMTP / Email Alerts)
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "alertas@licitlens.pe"
    SMTP_FROM_NAME: str = "LicitLens Alertas IA"
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    MAIL_DRY_RUN: bool = True  # True para registrar en logs sin conectar a servidor SMTP real
    FRONTEND_URL: str = "http://localhost:5173"

    # Configuración Pydantic: busca .env en CWD o relativo al directorio backend
    model_config = SettingsConfigDict(
        env_file=(
            os.path.join(os.path.dirname(__file__), "..", ".env"),
            ".env",
            "backend/.env"
        ),
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instancia singleton para ser importada en toda la aplicación
settings = Settings()
