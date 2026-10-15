import os
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

    # Servidor Web FastAPI
    HOST: str = "0.0.0.0"
    PORT: int = 8000

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
