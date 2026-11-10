"""Database CRUD operations and financial statistics calculations."""

import calendar
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import RecurringTransaction, Transaction, User


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
        next_d = d + timedelta(months=1) if hasattr(timedelta, "months") else d + timedelta(days=30)
    return next_d.isoformat()


# ---------------------------------------------------------------------------
# User Operations
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
            name=name,
            phone=phone,
            country_code=country_code,
            country_name=country_name,
            currency=currency,
            timezone=tz_name,
            language=language,
            is_registered=is_registered,
        )
        session.add(user)
    else:
        user.name = name
        if phone is not None:
            user.phone = phone
        user.country_code = country_code
        user.country_name = country_name
        user.currency = currency
        user.timezone = tz_name
        user.language = language
        user.is_registered = is_registered

    await session.commit()
    await session.refresh(user)
    return user


async def update_user_fields(session: AsyncSession, telegram_id: int, **kwargs) -> Optional[User]:
    user = await get_user_by_telegram_id(session, telegram_id)
    if not user:
        return None
    for key, value in kwargs.items():
        if hasattr(user, key):
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
# Transaction Operations
# ---------------------------------------------------------------------------


async def add_transaction(
    session: AsyncSession,
    user_id: int,
    tx_type: str,
    amount: Decimal | float | str,
    currency: str,
    description: str = "",
    recurring_id: Optional[int] = None,
    created_at: Optional[datetime] = None,
) -> Transaction:
    dec_amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    tx = Transaction(
        user_id=user_id,
        tx_type=tx_type,
        amount=abs(dec_amount),
        currency=currency.upper(),
        description=description.strip(),
        recurring_id=recurring_id,
        created_at=created_at or datetime.now(timezone.utc),
    )
    session.add(tx)
    await session.commit()
    await session.refresh(tx)
    return tx


async def get_transaction_by_id(
    session: AsyncSession, tx_id: int, user_id: Optional[int] = None
) -> Optional[Transaction]:
    stmt = select(Transaction).where(Transaction.id == tx_id)
    if user_id is not None:
        stmt = stmt.where(Transaction.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_transaction(
    session: AsyncSession,
    tx_id: int,
    user_id: int,
    amount: Optional[Decimal | float | str] = None,
    description: Optional[str] = None,
    tx_type: Optional[str] = None,
) -> Optional[Transaction]:
    tx = await get_transaction_by_id(session, tx_id, user_id=user_id)
    if not tx:
        return None
    if amount is not None:
        tx.amount = abs(Decimal(str(amount)).quantize(Decimal("0.01")))
    if description is not None:
        tx.description = description.strip()
    if tx_type in ("expense", "income"):
        tx.tx_type = tx_type
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
    income_stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.user_id == user_id,
        Transaction.tx_type == "income",
    )
    expense_stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.user_id == user_id,
        Transaction.tx_type == "expense",
    )
    inc = Decimal(str((await session.execute(income_stmt)).scalar() or 0))
    exp = Decimal(str((await session.execute(expense_stmt)).scalar() or 0))
    return (inc - exp).quantize(Decimal("0.01"))


async def get_user_statistics(
    session: AsyncSession, user: User, reference_utc: Optional[datetime] = None
) -> FinancialStats:
    """Compute day, week, month, and all-time statistics in user's local timezone."""
    tz = get_user_tz(user.timezone)
    now_utc = reference_utc or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    now_local = now_utc.astimezone(tz)

    # Start of today in user's local timezone -> UTC
    start_of_day_local = datetime.combine(now_local.date(), time.min, tzinfo=tz)
    # Start of ISO week (Monday) in user's local timezone
    days_since_monday = now_local.weekday()
    start_of_week_local = datetime.combine(
        now_local.date() - timedelta(days=days_since_monday), time.min, tzinfo=tz
    )
    # Start of current month in user's local timezone
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

    for tx in txs:
        amt = Decimal(str(tx.amount)).quantize(Decimal("0.01"))
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
    )


# ---------------------------------------------------------------------------
# Recurring Transaction Operations
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
    dec_amount = abs(Decimal(str(amount)).quantize(Decimal("0.01")))
    rec = RecurringTransaction(
        user_id=user_id,
        title=title.strip(),
        amount=dec_amount,
        currency=currency.upper(),
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
    session: AsyncSession, rec_id: int, user_id: Optional[int] = None
) -> Optional[RecurringTransaction]:
    stmt = select(RecurringTransaction).where(RecurringTransaction.id == rec_id)
    if user_id is not None:
        stmt = stmt.where(RecurringTransaction.user_id == user_id)
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
    """Check and execute any due active recurring transactions for a user."""
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
        # Process all missed occurrences up to today (capped at 12 iterations for safety)
        iterations = 0
        while rec.next_run_date <= today_str and iterations < 12:
            iterations += 1
            tx = Transaction(
                user_id=user.id,
                tx_type=rec.tx_type,
                amount=rec.amount,
                currency=rec.currency,
                description=f"🔄 {rec.title}",
                recurring_id=rec.id,
                created_at=datetime.now(timezone.utc),
            )
            session.add(tx)
            rec.next_run_date = advance_date(rec.next_run_date, rec.period)
            await session.flush()
            executed.append((rec, tx))

    if executed:
        await session.commit()
    return executed

