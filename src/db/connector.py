import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

try:
    DATABASE_URL = os.getenv("DATABASE_URL")
except Exception as e:
    raise ValueError("DATABASE_URL environment variable is not set") from e

# Pooling env variables
POOL_PRE_PING = os.getenv("POOL_PRE_PING", "TRUE").upper() == "TRUE"  # Check before every query
POOL_SIZE = int(os.getenv("POOL_SIZE", 5))  # Max connection count
MAX_OVERFLOW = int(os.getenv("MAX_OVERFLOW", 10))  # Max pool overflow connection count
POOL_RECYCLE = int(os.getenv("POOL_RECYCLE", 1800))  # 30 min default


class DatabaseConnector:
    """
    Hem lokal PostgreSQL hem de Supabase bağlantılarını yöneten,
    Thread-safe ve modüler veritabanı bağlayıcı sınıfı.
    """

    def __init__(self, db_url: str):
        self.db_url = db_url

        # Supabase veya uzak DB bağlantılarında kopmaları önlemek için pooling (havuz) ayarları
        self.engine = create_engine(
            self.db_url,
            pool_pre_ping=POOL_PRE_PING,
            pool_size=POOL_SIZE,
            max_overflow=MAX_OVERFLOW,
            pool_recycle=POOL_RECYCLE
        )

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
        Hata durumunda işlemleri geri alır (rollback), her durumda bağlantıyı kapatır.
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as exc:
            logger.exception(" => Database session error: %s", e)
            session.rollback()
            raise exc
        finally:
            session.close()


# --- 1. Singleton Example ---
db_connector = DatabaseConnector(DATABASE_URL)

# --- 2. SQLAlchemy ORM Base ---
Base = declarative_base()


# --- 3. FastAPI Dependency ---
def get_db():
    """
    FastAPI endpoint'lerinde 'Depends(get_db)' olarak kullanabileceğimiz
    ve her request-response döngüsünde taze bir session sağlayan yield yapısı.
    """
    with db_connector.get_db_session() as session:
        yield session
