import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_TYPE = os.getenv("DATABASE_TYPE")
if not DATABASE_TYPE:
    raise ValueError("CRITICAL: 'DATABASE_TYPE' environment variable is not set in .env file!")

if DATABASE_TYPE.upper() == "SUPABASE":
    DATABASE_URL = os.getenv("SUPABASE_DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("SUPABASE_DATABASE_URL is missing in .env")

    POOL_PRE_PING = os.getenv("POOL_PRE_PING", "TRUE").upper() == "TRUE"
    POOL_SIZE = int(os.getenv("POOL_SIZE", 5))
    MAX_OVERFLOW = int(os.getenv("MAX_OVERFLOW", 10))
    POOL_RECYCLE = int(os.getenv("POOL_RECYCLE", 1800))

elif DATABASE_TYPE.upper() == "POSTGRESQL":
    DATABASE_URL = os.getenv("LOCAL_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/smart_components")

    POOL_PRE_PING = True
    POOL_SIZE = int(os.getenv("POOL_SIZE", 10))
    MAX_OVERFLOW = int(os.getenv("MAX_OVERFLOW", 20))
    POOL_RECYCLE = -1
else:
    raise ValueError(f"Unknown DATABASE_TYPE: {DATABASE_TYPE}. Use 'SUPABASE' or 'POSTGRESQL'.")


class DatabaseConnector:
    """
    Hem lokal PostgreSQL hem de Supabase bağlantılarını yöneten,
    Thread-safe ve modüler veritabanı bağlayıcı sınıfı.
    """

    def __init__(self, db_url: str):
        self.db_url = db_url

        # SQLAlchemy Engine
        engine_kwargs = {
            "pool_pre_ping": POOL_PRE_PING,
            "pool_size": POOL_SIZE,
            "max_overflow": MAX_OVERFLOW
        }

        if POOL_RECYCLE > 0:
            engine_kwargs["pool_recycle"] = POOL_RECYCLE

        self.engine = create_engine(self.db_url, **engine_kwargs)

        # Session factory
        self._session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    @contextmanager
    def get_db_session(self):
        """
        Güvenli bir şekilde veritabanı oturumu açıp kapatan Context Manager.
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as exc:
            logger.exception(" => Database session error: %s", exc)
            session.rollback()
            raise exc
        finally:
            session.close()


# --- 1. Singleton Instance ---
db_connector = DatabaseConnector(DATABASE_URL)

# --- 2. SQLAlchemy ORM Base ---
Base = declarative_base()
