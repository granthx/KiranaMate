"""
Database models for KiranaMate — MerchantMind AI
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    DateTime, Text, JSON, ForeignKey, Enum
)
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.types import TypeDecorator, CHAR
import uuid
import enum


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            from sqlalchemy.dialects.postgresql import UUID as PG_UUID
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(str(value)).int
            else:
                return "%.32x" % value.int

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(str(value))
        return value


class Base(DeclarativeBase):
    pass


class Merchant(Base):
    __tablename__ = "merchants"

    id          = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name        = Column(String(200), nullable=False)
    shop_name   = Column(String(200), nullable=False)
    phone       = Column(String(15), unique=True, nullable=False)  # WhatsApp number
    address     = Column(Text)
    pin_code    = Column(String(10))
    city        = Column(String(100))
    paytm_mid   = Column(String(100))                 # Paytm Merchant ID
    language    = Column(String(20), default="hi")    # hi, en, etc.
    autonomous_mode = Column(Boolean, default=False)  # Auto-execute without approval
    created_at  = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="merchant")
    khata_entries = relationship("KhataEntry", back_populates="merchant")
    inventory    = relationship("InventoryItem", back_populates="merchant")
    campaigns    = relationship("Campaign", back_populates="merchant")
    customers    = relationship("Customer", back_populates="merchant")


class Transaction(Base):
    __tablename__ = "transactions"

    id           = Column(GUID(), primary_key=True, default=uuid.uuid4)
    merchant_id  = Column(GUID(), ForeignKey("merchants.id"), nullable=False)
    txn_id       = Column(String(100), unique=True)   # Paytm transaction ID
    amount       = Column(Float, nullable=False)
    category     = Column(String(100))                # dairy, snacks, staples, etc.
    sku_id       = Column(String(100))
    payment_mode = Column(String(50))                 # upi, card, cash
    customer_id  = Column(GUID(), ForeignKey("customers.id"), nullable=True)
    txn_time     = Column(DateTime, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    merchant     = relationship("Merchant", back_populates="transactions")
    customer     = relationship("Customer", back_populates="transactions")


class Customer(Base):
    __tablename__ = "customers"

    id           = Column(GUID(), primary_key=True, default=uuid.uuid4)
    merchant_id  = Column(GUID(), ForeignKey("merchants.id"), nullable=False)
    name         = Column(String(200))
    phone        = Column(String(15))
    segment      = Column(String(50), default="regular")  # regular, vip, occasional
    avg_spend    = Column(Float, default=0.0)
    pay_behavior = Column(String(50), default="on_time")  # on_time, delayed, defaulter
    warmth_score = Column(Float, default=0.5)             # 0-1, Cognee-updated
    last_txn_at  = Column(DateTime)
    created_at   = Column(DateTime, default=datetime.utcnow)

    merchant     = relationship("Merchant", back_populates="customers")
    transactions = relationship("Transaction", back_populates="customer")
    khata_entries = relationship("KhataEntry", back_populates="customer")


class KhataEntry(Base):
    """Informal credit tracking (Udhar/Khata)"""
    __tablename__ = "khata_entries"

    id           = Column(GUID(), primary_key=True, default=uuid.uuid4)
    merchant_id  = Column(GUID(), ForeignKey("merchants.id"), nullable=False)
    customer_id  = Column(GUID(), ForeignKey("customers.id"), nullable=False)
    amount       = Column(Float, nullable=False)
    description  = Column(Text)
    due_date     = Column(DateTime)
    status       = Column(String(20), default="pending")  # pending, paid, disputed
    reminder_count = Column(Integer, default=0)
    last_reminder_at = Column(DateTime)
    paid_at      = Column(DateTime)
    created_at   = Column(DateTime, default=datetime.utcnow)

    merchant     = relationship("Merchant", back_populates="khata_entries")
    customer     = relationship("Customer", back_populates="khata_entries")


class InventoryItem(Base):
    __tablename__ = "inventory"

    id           = Column(GUID(), primary_key=True, default=uuid.uuid4)
    merchant_id  = Column(GUID(), ForeignKey("merchants.id"), nullable=False)
    sku_id       = Column(String(100), nullable=False)
    name         = Column(String(200), nullable=False)
    category     = Column(String(100))
    quantity     = Column(Integer, default=0)
    unit_cost    = Column(Float)
    selling_price = Column(Float)
    margin_pct   = Column(Float)
    expiry_date  = Column(DateTime)
    reorder_point = Column(Integer, default=10)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    merchant     = relationship("Merchant", back_populates="inventory")


class SalesBaseline(Base):
    """Rolling 4-week baseline for anomaly detection"""
    __tablename__ = "sales_baselines"

    id           = Column(GUID(), primary_key=True, default=uuid.uuid4)
    merchant_id  = Column(GUID(), ForeignKey("merchants.id"), nullable=False)
    category     = Column(String(100))
    day_of_week  = Column(Integer)   # 0=Monday, 6=Sunday
    hour         = Column(Integer)   # 0-23
    avg_revenue  = Column(Float)
    stddev       = Column(Float)
    sample_count = Column(Integer)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Anomaly(Base):
    __tablename__ = "anomalies"

    id           = Column(GUID(), primary_key=True, default=uuid.uuid4)
    merchant_id  = Column(GUID(), ForeignKey("merchants.id"), nullable=False)
    category     = Column(String(100))
    severity     = Column(String(20))   # CRITICAL, WARNING, INFO
    deviation_pct = Column(Float)
    expected_rev = Column(Float)
    actual_rev   = Column(Float)
    description  = Column(Text)
    status       = Column(String(20), default="open")  # open, resolved, ignored
    alert_sent   = Column(Boolean, default=False)
    detected_at  = Column(DateTime, default=datetime.utcnow)
    resolved_at  = Column(DateTime)


class Campaign(Base):
    __tablename__ = "campaigns"

    id            = Column(GUID(), primary_key=True, default=uuid.uuid4)
    merchant_id   = Column(GUID(), ForeignKey("merchants.id"), nullable=False)
    goal          = Column(Text)                        # Raw merchant voice/text goal
    category      = Column(String(100))
    sku_ids       = Column(JSON)                        # List of targeted SKU IDs
    discount_pct  = Column(Float)
    customers_targeted = Column(Integer)
    customers_converted = Column(Integer, default=0)
    revenue_recovered = Column(Float, default=0.0)
    poster_url    = Column(String(500))
    wa_message    = Column(Text)
    status        = Column(String(30), default="pending")  # pending, approved, live, completed, cancelled
    approval_required = Column(Boolean, default=True)
    approved_at   = Column(DateTime)
    launched_at   = Column(DateTime)
    completed_at  = Column(DateTime)
    created_at    = Column(DateTime, default=datetime.utcnow)
    langgraph_thread_id = Column(String(200))           # LangGraph state thread

    merchant      = relationship("Merchant", back_populates="campaigns")


class HealthReport(Base):
    __tablename__ = "health_reports"

    id            = Column(GUID(), primary_key=True, default=uuid.uuid4)
    merchant_id   = Column(GUID(), ForeignKey("merchants.id"), nullable=False)
    week_start    = Column(DateTime)
    week_end      = Column(DateTime)
    health_score  = Column(Float)           # 0-100
    total_revenue = Column(Float)
    revenue_trend = Column(Float)           # % change vs last week
    top_products  = Column(JSON)
    anomalies_count = Column(Integer)
    khata_recovered = Column(Float)
    ai_recommendation = Column(Text)
    pdf_url       = Column(String(500))
    delivered_at  = Column(DateTime)
    created_at    = Column(DateTime, default=datetime.utcnow)
