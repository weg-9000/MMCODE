import asyncio
import sys
import os
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from dotenv import load_dotenv

# 1. 설정 로드
load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import Base, get_database_url 
from app.models.models import * 

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# ----------------------------------------------------------------------
# 중요: config.set_main_option을 호출하지 않습니다.
# (Offline 모드를 사용하지 않는다면 굳이 필요 없으며, % 오류의 원인이 됩니다)
# ----------------------------------------------------------------------

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # Offline 모드에서도 get_database_url()을 직접 호출하여 사용
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    db_url = get_database_url()

    # URL 객체로 변환 (문자열 처리 실수 방지)
    from sqlalchemy.engine.url import make_url
    url_obj = make_url(db_url)
    
    print(f"DEBUG: Connecting to host: {url_obj.host}")

    connectable = create_async_engine(
        url_obj,
        poolclass=pool.NullPool,
        # connect_args 딕셔너리 구조 정확히 확인
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        }
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
