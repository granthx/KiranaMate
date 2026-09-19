"""
Async PostgreSQL database connection for KiranaMate
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from db.models import Base
from dotenv import load_dotenv

load_dotenv()
from pathlib import Path

is_serverless = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
if is_serverless:
    DEFAULT_SQLITE_PATH = Path("/tmp/kiranamate.db")
else:
    DEFAULT_SQLITE_PATH = Path(__file__).resolve().parent.parent / "kiranamate.db"

DEFAULT_DB_URL = f"sqlite+aiosqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"

DATABASE_URL = os.getenv("DATABASE_URL") or DEFAULT_DB_URL

connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}
    engine = create_async_engine(
        DATABASE_URL,
        echo=os.getenv("DEBUG", "false").lower() == "true",
        connect_args=connect_args,
    )
else:
    engine = create_async_engine(
        DATABASE_URL,
        echo=os.getenv("DEBUG", "false").lower() == "true",
        poolclass=NullPool,
    )

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Create all tables on startup and seed if empty"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Auto-seed demo data if database was just created
        from db.models import Merchant
        from sqlalchemy import select
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Merchant))
            if not result.scalars().first():
                from db.seed import seed
                await seed()
                print("✅ Auto-seeded database for demo")
    except Exception as e:
        print(f"⚠️ Database initialization error: {e}")


async def get_db():
    """FastAPI dependency: yields a DB session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
