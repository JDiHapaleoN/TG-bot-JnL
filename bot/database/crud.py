"""Database CRUD operations, idempotency guarantees, and exact Decimal financial statistics."""

import calendar
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    ProcessedUpdate,
    RecurringTransaction,
    Transaction,
    User,
)
from bot.services.categories import detect_category


@dataclass
class FinancialStats:
    balance: Decimal
    total_income: Decimal
    total_expense: Decimal
    net_diff: Decimal
    today_expense: Decimal
    today_income: Decimal
    week_expense: Decimal
    week_income: Decimal
    month_expense: Decimal
    month_income: Decimal
    month_by_category: Dict[str, Decimal] = field(default_factory=dict)


def get_user_tz(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("UTC")


def to_local_datetime(dt: datetime, tz_name: str) -> datetime:
    tz = get_user_tz(tz_name)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz)


def local_now(tz_name: str) -> datetime:
    return datetime.now(timezone.utc).astimezone(get_user_tz(tz_name))


def advance_date(current_date_str: str, period: str) -> str:
    """Calculate the next run date ('YYYY-MM-DD') based on period."""
    d = date.fromisoformat(current_date_str)
    if period == "daily":
        next_d = d + timedelta(days=1)
    elif period == "weekly":
        next_d = d + timedelta(weeks=1)
    elif period == "monthly":
        year = d.year + (d.month // 12)
        month = (d.month % 12) + 1
        last_day = calendar.monthrange(year, month)[1]
        next_d = date(year, month, min(d.day, last_day))
    elif period == "yearly":
        year = d.year + 1
        last_day = calendar.monthrange(year, d.month)[1]
        next_d = date(year, d.month, min(d.day, last_day))
    else:
        next_d = d + timedelta(days=30)
    return next_d.isoformat()


def _to_exact_decimal(value: Decimal | float | int | str) -> Decimal:
    """Convert numeric input to exact 2-decimal-place Decimal without float artifacts."""
    if isinstance(value, float):
        value = f"{value:.2f}"
    try:
        dec = Decimal(str(value).strip()).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid monetary amount: {value}") from exc
    return dec


# ---------------------------------------------------------------------------
# Telegram Update Idempotency Operations
# ---------------------------------------------------------------------------


async def is_update_processed(session: AsyncSession, update_id: int) -> bool:
    if not update_id:
        return False
    stmt = select(ProcessedUpdate.update_id).where(ProcessedUpdate.update_id == update_id)
    res = await session.execute(stmt)
    return res.scalar_one_or_none() is not None


async def mark_update_processed(
    session: AsyncSession, update_id: int, telegram_id: Optional[int] = None
) -> bool:
    """
    Record an update_id as processed. Returns True if newly recorded,
    or False if it was already processed.
    """
    if not update_id:
        return True
    if await is_update_processed(session, update_id):
        return False
    try:
        rec = ProcessedUpdate(
            update_id=update_id,
            telegram_id=telegram_id,
            processed_at=datetime.now(timezone.utc),
        )
        session.add(rec)
        await session.commit()
        return True
    except IntegrityError:
        await session.rollback()
        return False


# ---------------------------------------------------------------------------
# User Operations (Strictly keyed by immutable telegram_id)
# ---------------------------------------------------------------------------


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_or_update_user(
    session: AsyncSession,
    telegram_id: int,
    name: str,
    phone: Optional[str] = None,
    country_code: str = "DE",
    country_name: str = "Germany",
    currency: str = "EUR",
    tz_name: str = "Europe/Berlin",
    language: str = "ru",
    is_registered: bool = True,
) -> User:
    user = await get_user_by_telegram_id(session, telegram_id)
    if user is None:
        user = User(
            telegram_id=telegram_id,
            name=(name or "User").strip()[:120],
            phone=phone,
            country_code=(country_code or "DE").upper()[:8],
            country_name=(country_name or "Germany")[:100],
            currency=(currency or "EUR").upper()[:8],
            timezone=(tz_name or "Europe/Berlin")[:64],
            language=(language or "ru")[:8],
            is_registered=is_registered,
        )
        session.add(user)
        try:
            await session.commit()
            await session.refresh(user)
            return user
        except IntegrityError:
            await session.rollback()
            user = await get_user_by_telegram_id(session, telegram_id)
            if user is None:
                raise

    user.name = (name or user.name or "User").strip()[:120]
    if phone is not None:
        user.phone = phone
    user.country_code = (country_code or user.country_code or "DE").upper()[:8]
    user.country_name = (country_name or user.country_name or "Germany")[:100]
    user.currency = (currency or user.currency or "EUR").upper()[:8]
    user.timezone = (tz_name or user.timezone or "Europe/Berlin")[:64]
    user.language = (language or user.language or "ru")[:8]
    user.is_registered = is_registered

    await session.commit()
    await session.refresh(user)
    return user


async def update_user_fields(session: AsyncSession, telegram_id: int, **kwargs) -> Optional[User]:
    user = await get_user_by_telegram_id(session, telegram_id)
    if not user:
        return None
    for key, value in kwargs.items():
        if hasattr(user, key) and key not in ("id", "telegram_id", "created_at"):
            setattr(user, key, value)
    await session.commit()
    await session.refresh(user)
    return user


async def delete_user_account(session: AsyncSession, telegram_id: int) -> bool:
    user = await get_user_by_telegram_id(session, telegram_id)
    if not user:
        return False
    await session.delete(user)
    await session.commit()
    return True


async def get_all_registered_users(session: AsyncSession) -> List[User]:
    stmt = select(User).where(User.is_registered.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Transaction Operations (Atomic, Verified, Idempotent, Owner-Isolated)
# ---------------------------------------------------------------------------


async def get_transaction_by_idempotency_key(
    session: AsyncSession, idempotency_key: str
) -> Optional[Transaction]:
    stmt = select(Transaction).where(Transaction.idempotency_key == idempotency_key)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def add_transaction(
    session: AsyncSession,
    user_id: int,
    tx_type: str,
    amount: Decimal | float | str,
    currency: str,
    description: str = "",
    category: Optional[str] = None,
    recurring_id: Optional[int] = None,
    idempotency_key: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> Transaction:
    if tx_type not in ("expense", "income"):
        raise ValueError(f"Invalid transaction type: {tx_type}")

    dec_amount = _to_exact_decimal(amount)
    if dec_amount <= Decimal("0.00") or dec_amount > Decimal("999999999.99"):
        raise ValueError(f"Transaction amount out of allowed range: {dec_amount}")

    if idempotency_key:
        existing = await get_transaction_by_idempotency_key(session, idempotency_key)
        if existing is not None:
            return existing

    clean_desc = (description or "").strip()[:255]
    resolved_cat = category or detect_category(clean_desc, tx_type=tx_type)

    tx = Transaction(
        user_id=user_id,
        tx_type=tx_type,
        amount=dec_amount,
        currency=(currency or "EUR").upper().strip()[:8],
        category=resolved_cat,
        description=clean_desc,
        recurring_id=recurring_id,
        idempotency_key=idempotency_key,
        created_at=created_at or datetime.now(timezone.utc),
    )
    session.add(tx)
    try:
        await session.commit()
        await session.refresh(tx)
    except IntegrityError:
        await session.rollback()
        if idempotency_key:
            existing = await get_transaction_by_idempotency_key(session, idempotency_key)
            if existing is not None:
                return existing
        raise

    if tx.id is None:
        raise RuntimeError("Transaction commit did not produce a valid database ID")
    return tx


async def get_transaction_by_id(
    session: AsyncSession, tx_id: int, user_id: int
) -> Optional[Transaction]:
    """Retrieve a transaction strictly owned by user_id."""
    stmt = select(Transaction).where(
        Transaction.id == tx_id,
        Transaction.user_id == user_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_transaction(
    session: AsyncSession,
    tx_id: int,
    user_id: int,
    amount: Optional[Decimal | float | str] = None,
    description: Optional[str] = None,
    tx_type: Optional[str] = None,
    category: Optional[str] = None,
) -> Optional[Transaction]:
    tx = await get_transaction_by_id(session, tx_id, user_id=user_id)
    if not tx:
        return None
    if amount is not None:
        dec_amt = _to_exact_decimal(amount)
        if dec_amt <= Decimal("0.00") or dec_amt > Decimal("999999999.99"):
            raise ValueError(f"Invalid updated amount: {dec_amt}")
        tx.amount = dec_amt
    if tx_type in ("expense", "income"):
        tx.tx_type = tx_type
    if description is not None:
        tx.description = description.strip()[:255]
        if category is None:
            tx.category = detect_category(tx.description, tx_type=tx.tx_type)
    if category is not None:
        tx.category = category.strip()[:64]

    await session.commit()
    await session.refresh(tx)
    return tx


async def delete_transaction(session: AsyncSession, tx_id: int, user_id: int) -> bool:
    tx = await get_transaction_by_id(session, tx_id, user_id=user_id)
    if not tx:
        return False
    await session.delete(tx)
    await session.commit()
    return True


async def get_user_transactions(
    session: AsyncSession,
    user_id: int,
    limit: int = 10,
    offset: int = 0,
) -> Tuple[List[Transaction], int]:
    count_stmt = select(func.count(Transaction.id)).where(Transaction.user_id == user_id)
    total = (await session.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(desc(Transaction.created_at), desc(Transaction.id))
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all()), int(total)


async def get_user_balance(session: AsyncSession, user_id: int) -> Decimal:
    """
    Calculate user balance using exact Python Decimal arithmetic
    (avoiding SQLite internal floating-point SUM() inaccuracies).
    """
    stmt = select(Transaction.tx_type, Transaction.amount).where(
        Transaction.user_id == user_id
    )
    rows = (await session.execute(stmt)).all()
    balance = Decimal("0.00")
    for tx_type, raw_amt in rows:
        amt = _to_exact_decimal(raw_amt)
        if tx_type == "income":
            balance += amt
        else:
            balance -= amt
    return balance.quantize(Decimal("0.01"))


async def get_user_statistics(
    session: AsyncSession, user: User, reference_utc: Optional[datetime] = None
) -> FinancialStats:
    """Compute day, week, month, and all-time statistics in user's local timezone with exact Decimal math."""
    tz = get_user_tz(user.timezone)
    now_utc = reference_utc or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    now_local = now_utc.astimezone(tz)

    start_of_day_local = datetime.combine(now_local.date(), time.min, tzinfo=tz)
    days_since_monday = now_local.weekday()
    start_of_week_local = datetime.combine(
        now_local.date() - timedelta(days=days_since_monday), time.min, tzinfo=tz
    )
    start_of_month_local = datetime.combine(
        now_local.date().replace(day=1), time.min, tzinfo=tz
    )

    stmt = select(Transaction).where(Transaction.user_id == user.id)
    result = await session.execute(stmt)
    txs = list(result.scalars().all())

    zero = Decimal("0.00")
    total_income = zero
    total_expense = zero
    today_expense = zero
    today_income = zero
    week_expense = zero
    week_income = zero
    month_expense = zero
    month_income = zero
    month_by_category: Dict[str, Decimal] = {}

    for tx in txs:
        amt = _to_exact_decimal(tx.amount)
        tx_local = to_local_datetime(tx.created_at, user.timezone)
        is_inc = tx.tx_type == "income"

        if is_inc:
            total_income += amt
        else:
            total_expense += amt

        if tx_local >= start_of_day_local:
            if is_inc:
                today_income += amt
            else:
                today_expense += amt

        if tx_local >= start_of_week_local:
            if is_inc:
                week_income += amt
            else:
                week_expense += amt

        if tx_local >= start_of_month_local:
            if is_inc:
                month_income += amt
            else:
                month_expense += amt
                cat_key = getattr(tx, "category", None) or "other"
                month_by_category[cat_key] = (
                    month_by_category.get(cat_key, zero) + amt
                ).quantize(Decimal("0.01"))

    balance = (total_income - total_expense).quantize(Decimal("0.01"))
    net_diff = (month_income - month_expense).quantize(Decimal("0.01"))

    return FinancialStats(
        balance=balance,
        total_income=total_income.quantize(Decimal("0.01")),
        total_expense=total_expense.quantize(Decimal("0.01")),
        net_diff=net_diff,
        today_expense=today_expense.quantize(Decimal("0.01")),
        today_income=today_income.quantize(Decimal("0.01")),
        week_expense=week_expense.quantize(Decimal("0.01")),
        week_income=week_income.quantize(Decimal("0.01")),
        month_expense=month_expense.quantize(Decimal("0.01")),
        month_income=month_income.quantize(Decimal("0.01")),
        month_by_category=month_by_category,
    )


# ---------------------------------------------------------------------------
# Recurring Transaction Operations (Idempotent & Owner-Isolated)
# ---------------------------------------------------------------------------


async def create_recurring_transaction(
    session: AsyncSession,
    user_id: int,
    title: str,
    amount: Decimal | float | str,
    currency: str,
    tx_type: str,
    period: str,
    next_run_date: str,
) -> RecurringTransaction:
    if tx_type not in ("expense", "income"):
        raise ValueError(f"Invalid recurring tx_type: {tx_type}")
    if period not in ("daily", "weekly", "monthly", "yearly"):
        raise ValueError(f"Invalid recurring period: {period}")
    date.fromisoformat(next_run_date)

    dec_amount = _to_exact_decimal(amount)
    if dec_amount <= Decimal("0.00") or dec_amount > Decimal("999999999.99"):
        raise ValueError(f"Recurring amount out of range: {dec_amount}")

    rec = RecurringTransaction(
        user_id=user_id,
        title=title.strip()[:120],
        amount=dec_amount,
        currency=(currency or "EUR").upper()[:8],
        tx_type=tx_type,
        period=period,
        next_run_date=next_run_date,
        is_active=True,
    )
    session.add(rec)
    await session.commit()
    await session.refresh(rec)
    return rec


async def get_user_recurring_transactions(
    session: AsyncSession, user_id: int
) -> List[RecurringTransaction]:
    stmt = (
        select(RecurringTransaction)
        .where(RecurringTransaction.user_id == user_id)
        .order_by(RecurringTransaction.next_run_date.asc(), RecurringTransaction.id.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_recurring_by_id(
    session: AsyncSession, rec_id: int, user_id: int
) -> Optional[RecurringTransaction]:
    stmt = select(RecurringTransaction).where(
        RecurringTransaction.id == rec_id,
        RecurringTransaction.user_id == user_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def toggle_recurring_transaction(
    session: AsyncSession, rec_id: int, user_id: int
) -> Optional[RecurringTransaction]:
    rec = await get_recurring_by_id(session, rec_id, user_id=user_id)
    if not rec:
        return None
    rec.is_active = not rec.is_active
    await session.commit()
    await session.refresh(rec)
    return rec


async def delete_recurring_transaction(
    session: AsyncSession, rec_id: int, user_id: int
) -> bool:
    rec = await get_recurring_by_id(session, rec_id, user_id=user_id)
    if not rec:
        return False
    await session.delete(rec)
    await session.commit()
    return True


async def process_due_recurring_for_user(
    session: AsyncSession, user: User, current_local_date: Optional[str] = None
) -> List[Tuple[RecurringTransaction, Transaction]]:
    """
    Idempotently check and execute any due active recurring transactions for a user.
    Uses a unique idempotency_key 'rec:{rec.id}:{scheduled_date}' so a server restart
    or concurrent tick on the same day never creates duplicate transactions.
    """
    today_str = current_local_date or local_now(user.timezone).date().isoformat()
    stmt = select(RecurringTransaction).where(
        RecurringTransaction.user_id == user.id,
        RecurringTransaction.is_active.is_(True),
        RecurringTransaction.next_run_date <= today_str,
    )
    result = await session.execute(stmt)
    due_items = list(result.scalars().all())

    executed: List[Tuple[RecurringTransaction, Transaction]] = []
    for rec in due_items:
        iterations = 0
        while rec.next_run_date <= today_str and iterations < 36:
            iterations += 1
            scheduled_date = rec.next_run_date
            idem_key = f"rec:{rec.id}:{scheduled_date}"

            existing_tx = await get_transaction_by_idempotency_key(session, idem_key)
            if existing_tx is None:
                cat = detect_category(rec.title, tx_type=rec.tx_type)
                tx = Transaction(
                    user_id=user.id,
                    tx_type=rec.tx_type,
                    amount=rec.amount,
                    currency=rec.currency,
                    category=cat,
                    description=f"🔄 {rec.title}",
                    recurring_id=rec.id,
                    idempotency_key=idem_key,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(tx)
                rec.next_run_date = advance_date(scheduled_date, rec.period)
                try:
                    await session.commit()
                    await session.refresh(tx)
                    executed.append((rec, tx))
                except IntegrityError:
                    await session.rollback()
                    await session.refresh(rec)
                    break
            else:
                # Already recorded for this scheduled_date; advance next_run_date safely
                rec.next_run_date = advance_date(scheduled_date, rec.period)
                await session.commit()

    return executed
