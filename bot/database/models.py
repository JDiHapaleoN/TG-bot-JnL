"""SQLAlchemy 2.0 ORM models for Users, Transactions, and Recurring Transactions."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    country_code: Mapped[str] = mapped_column(String(8), nullable=False, default="DE")
    country_name: Mapped[str] = mapped_column(String(100), nullable=False, default="Germany")
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="EUR")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Berlin")
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="ru")

    notify_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    daily_reminder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reminder_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    last_reminder_date: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    is_registered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    recurring_transactions: Mapped[List["RecurringTransaction"]] = relationship(
        "RecurringTransaction", back_populates="user", cascade="all, delete-orphan"
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    tx_type: Mapped[str] = mapped_column(String(16), nullable=False)  # 'expense' | 'income'
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="EUR")
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    recurring_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("recurring_transactions.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False, default=utc_now
    )

    user: Mapped["User"] = relationship("User", back_populates="transactions")


class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="EUR")
    tx_type: Mapped[str] = mapped_column(String(16), nullable=False)  # 'expense' | 'income'
    period: Mapped[str] = mapped_column(String(16), nullable=False)  # 'daily' | 'weekly' | 'monthly' | 'yearly'
    next_run_date: Mapped[str] = mapped_column(String(16), index=True, nullable=False)  # 'YYYY-MM-DD'
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    user: Mapped["User"] = relationship("User", back_populates="recurring_transactions")

