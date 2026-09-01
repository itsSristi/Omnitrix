from logging.config import fileConfig
import os

from dotenv import load_dotenv

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context


# --------------------------------------------------
# Load .env
# --------------------------------------------------

load_dotenv()


# --------------------------------------------------
# Import database Base
# --------------------------------------------------

from app.database.database import Base


# --------------------------------------------------
# Import ALL SQLAlchemy models
# --------------------------------------------------

from app.models import (
    User
)


# --------------------------------------------------
# Alembic Config object
# --------------------------------------------------

config = context.config


# --------------------------------------------------
# Get DATABASE_URL from .env
# --------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")


if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL is not set in the .env file"
    )


# --------------------------------------------------
# Tell Alembic which database to use
# --------------------------------------------------

config.set_main_option(
    "sqlalchemy.url",
    DATABASE_URL.replace("%", "%%")
)


# --------------------------------------------------
# Configure logging
# --------------------------------------------------

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# --------------------------------------------------
# SQLAlchemy metadata
# --------------------------------------------------

target_metadata = Base.metadata


# --------------------------------------------------
# Offline migrations
# --------------------------------------------------

def run_migrations_offline() -> None:

    url = config.get_main_option(
        "sqlalchemy.url"
    )

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named"
        },
    )

    with context.begin_transaction():
        context.run_migrations()


# --------------------------------------------------
# Online migrations
# --------------------------------------------------

def run_migrations_online() -> None:

    connectable = engine_from_config(
        config.get_section(
            config.config_ini_section,
            {}
        ),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# --------------------------------------------------
# Run migration
# --------------------------------------------------

if context.is_offline_mode():

    run_migrations_offline()

else:

    run_migrations_online()