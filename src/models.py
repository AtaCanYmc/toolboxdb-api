import uuid

from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    Boolean,
    Date,
    Numeric,
    DateTime,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from src.db import Base
from src.utils.time_utils import get_utc_now


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"
    CHATTER = "chatter"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default=UserRole.USER.value, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    components = relationship(
        "Component", back_populates="user", cascade="all, delete-orphan"
    )


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(
        DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now
    )
    components = relationship(
        "Component", back_populates="category", cascade="all, delete-orphan"
    )


class Component(Base):
    __tablename__ = "components"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user = relationship("User", back_populates="components")
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"))
    category = relationship("Category", back_populates="components")
    name = Column(String(255), nullable=False)
    quantity = Column(Integer, default=0)
    datasheet_url = Column(String, nullable=True)
    technical_specs = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(
        DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now
    )


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_name = Column(String(100), nullable=False)
    invoice_date = Column(Date, nullable=True)
    total_amount = Column(Numeric(10, 2), nullable=True)
    file_path = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    items = relationship(
        "InvoiceItem", back_populates="invoice", cascade="all, delete-orphan"
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE")
    )
    raw_name = Column(String, nullable=False)
    clean_name = Column(String(255), nullable=True)
    quantity = Column(Integer, nullable=False)
    category_name = Column(String(50), nullable=True)
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    invoice = relationship("Invoice", back_populates="items")
