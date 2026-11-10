"""Finite State Machine (FSM) states for aiogram 3."""

from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    language = State()
    name = State()
    phone = State()
    location = State()
    confirm = State()
    custom_country = State()
    custom_currency = State()
    custom_timezone = State()


class TransactionStates(StatesGroup):
    waiting_expense = State()
    waiting_income = State()
    editing_tx = State()


class RecurringStates(StatesGroup):
    waiting_title = State()
    waiting_amount = State()
    waiting_period = State()
    waiting_date = State()
    editing_title = State()
    editing_amount = State()
    editing_date = State()


class ProfileStates(StatesGroup):
    editing_name = State()
    editing_phone = State()
    editing_country = State()
    editing_currency = State()
    editing_timezone = State()

