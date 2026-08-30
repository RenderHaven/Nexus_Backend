from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

database_url = settings.DATABASE_URL

if database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )

engine = create_async_engine(
    database_url,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_recycle=3600,
)