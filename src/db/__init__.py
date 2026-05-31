from src.db.connector import DatabaseConnector, db_connector, Base
from .models import Category, Component, Invoice, InvoiceItem
from .schemas import (
    CategoryBase,
    CategoryResponse,
    ComponentBase,
    ComponentCreate,
    ComponentResponse,
    InvoiceBase,
    InvoiceResponse,
    InvoiceItemBase,
    InvoiceItemResponse,
)


# ---  FastAPI Dependency ---
def get_db():
    """
    FastAPI endpoint'lerinde 'Depends(get_db)' olarak kullanabileceğimiz
    ve her request-response döngüsünde taze bir session sağlayan yield yapısı.
    """
    with db_connector.get_db_session() as session:
        yield session


__all__ = [
    "db_connector",
    "get_db",
    "Base",
    "Category",
    "Component",
    "Invoice",
    "ComponentCreate",
    "ComponentResponse",
    "InvoiceBase",
    "InvoiceItemBase",
    "InvoiceItemResponse",
]
