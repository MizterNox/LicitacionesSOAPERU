"""
Entorno de migraciones Alembic (modo asíncrono con asyncpg).

- La URL de conexión se toma de `config.settings.DATABASE_URL` (.env), nunca de alembic.ini.
- `target_metadata` apunta a los modelos ORM para soportar `alembic revision --autogenerate`.

Uso (desde backend/):
    alembic upgrade head        # aplicar migraciones pendientes
    alembic downgrade -1        # revertir la última
    alembic current             # revisión aplicada en la BD
    alembic revision --autogenerate -m "descripcion"
"""
import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Asegurar que backend/src esté en el path (además de prepend_sys_path de alembic.ini)
_src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from config import settings  # noqa: E402
from database import Base  # noqa: E402
import models  # noqa: E402,F401  (registra todos los modelos en Base.metadata)

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Tablas heredadas que existen en la BD pero no son gestionadas por el ORM.
# Se excluyen del autogenerate para que nunca se propongan DROP accidentales.
LEGACY_TABLES = {"awards", "organizations", "tender_items"}


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table" and name in LEGACY_TABLES:
        return False
    return True


def run_migrations_offline() -> None:
    """Genera SQL sin conectarse (alembic upgrade head --sql)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
