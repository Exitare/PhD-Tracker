from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
from src.db import Base
import src.db.models
from urllib.parse import quote_plus

print(">>> Alembic env.py is executing...")
print(f">>> Loaded tables: {list(Base.metadata.tables.keys())}")

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

    # Determine environment
    mode: str = os.getenv("MODE", "dev")

    # Set DB URL automatically based on environment
    if mode != "dev":
        print(f">>> {mode} mode")
        user = os.getenv("DB_USER")
        password = quote_plus(os.environ.get("DB_PASSWORD"))
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "3306")
        name = os.getenv("DB_NAME")

        if not all([user, password, host, port, name]):
            raise RuntimeError("Missing one or more MySQL DB environment variables")

        db_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"
        config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    print(f"Loaded tables: {list(target_metadata.tables.keys())}")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
