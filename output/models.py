from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple


class AccountError(Exception):
    """
    Domain-specific exception for invalid account operations.

    Parameters
    ----------
    message : str
        Human-readable description of the error.
    code : str
        Machine-readable error code identifying the failure category.
    """

    def __init__(self, message: str, code: str) -> None:
        self.message = str(message)
        self.code = str(code)
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class TransactionType(str, Enum):
    ACCOUNT_CREATED = "ACCOUNT_CREATED"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class Transaction:
    transaction_type: TransactionType
    timestamp: datetime
    account_id: str
    amount: Optional[Decimal] = None
    post_cash_balance: Optional[Decimal] = None
    symbol: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    post_holding_quantity: Optional[int] = None
    metadata: Dict[str, str] = field(default_factory=dict)

    def create_account_created(self, account_id: str, timestamp: datetime) -> Transaction:
        return Transaction(
            transaction_type=TransactionType.ACCOUNT_CREATED,
            timestamp=_validate_timestamp(timestamp),
            account_id=_validate_account_id(account_id),
        )

    def create_deposit(
        self, amount: Decimal, post_cash_balance: Decimal, timestamp: datetime
    ) -> Transaction:
        amount = _validate_decimal(amount, "amount", non_negative=False)
        post_cash_balance = _validate_decimal(post_cash_balance, "post_cash_balance")
        return Transaction(
            transaction_type=TransactionType.DEPOSIT,
            timestamp=_validate_timestamp(timestamp),
            account_id=self.account_id,
            amount=amount,
            post_cash_balance=post_cash_balance,
        )

    def create_withdrawal(
        self, amount: Decimal, post_cash_balance: Decimal, timestamp: datetime
    ) -> Transaction:
        amount = _validate_decimal(amount, "amount", non_negative=False)
        post_cash_balance = _validate_decimal(post_cash_balance, "post_cash_balance")
        return Transaction(
            transaction_type=TransactionType.WITHDRAWAL,
            timestamp=_validate_timestamp(timestamp),
            account_id=self.account_id,
            amount=amount,
            post_cash_balance=post_cash_balance,
        )

    def create_buy(
        self,
        symbol: str,
        quantity: int,
        unit_price: Decimal,
        total_amount: Decimal,
        post_cash_balance: Decimal,
        post_holding_quantity: int,
        timestamp: datetime,
    ) -> Transaction:
        symbol = _validate_symbol(symbol)
        quantity = _validate_quantity(quantity)
        unit_price = _validate_decimal(unit_price, "unit_price")
        total_amount = _validate_decimal(total_amount, "total_amount")
        post_cash_balance = _validate_decimal(post_cash_balance, "post_cash_balance")
        post_holding_quantity = _validate_non_negative_int(
            post_holding_quantity, "post_holding_quantity"
        )
        _validate_price_quantity_consistency(unit_price, quantity, total_amount)
        return Transaction(
            transaction_type=TransactionType.BUY,
            timestamp=_validate_timestamp(timestamp),
            account_id=self.account_id,
            symbol=symbol,
            quantity=quantity,
            unit_price=unit_price,
            total_amount=total_amount,
            post_cash_balance=post_cash_balance,
            post_holding_quantity=post_holding_quantity,
        )

    def create_sell(
        self,
        symbol: str,
        quantity: int,
        unit_price: Decimal,
        total_amount: Decimal,
        post_cash_balance: Decimal,
        post_holding_quantity: int,
        timestamp: datetime,
    ) -> Transaction:
        symbol = _validate_symbol(symbol)
        quantity = _validate_quantity(quantity)
        unit_price = _validate_decimal(unit_price, "unit_price")
        total_amount = _validate_decimal(total_amount, "total_amount")
        post_cash_balance = _validate_decimal(post_cash_balance, "post_cash_balance")
        post_holding_quantity = _validate_non_negative_int(
            post_holding_quantity, "post_holding_quantity"
        )
        _validate_price_quantity_consistency(unit_price, quantity, total_amount)
        return Transaction(
            transaction_type=TransactionType.SELL,
            timestamp=_validate_timestamp(timestamp),
            account_id=self.account_id,
            symbol=symbol,
            quantity=quantity,
            unit_price=unit_price,
            total_amount=total_amount,
            post_cash_balance=post_cash_balance,
            post_holding_quantity=post_holding_quantity,
        )

    @property
    def is_account_created(self) -> bool:
        return self.transaction_type == TransactionType.ACCOUNT_CREATED

    @property
    def is_cash_transaction(self) -> bool:
        return self.transaction_type in {TransactionType.DEPOSIT, TransactionType.WITHDRAWAL}

    @property
    def is_trade(self) -> bool:
        return self.transaction_type in {TransactionType.BUY, TransactionType.SELL}


def _validate_timestamp(timestamp: datetime) -> datetime:
    if not isinstance(timestamp, datetime):
        raise AccountError("timestamp must be a datetime instance", "INVALID_TIMESTAMP")
    return timestamp


def _validate_account_id(account_id: str) -> str:
    if not isinstance(account_id, str) or not account_id.strip():
        raise AccountError("account_id must be a non-empty string", "INVALID_ACCOUNT_ID")
    return account_id.strip()


def _validate_symbol(symbol: str) -> str:
    if not isinstance(symbol, str) or not symbol.strip():
        raise AccountError("symbol must be a non-empty string", "INVALID_SYMBOL")
    return symbol.strip().upper()


def _validate_quantity(quantity: int) -> int:
    if not isinstance(quantity, int):
        raise AccountError("quantity must be an integer", "INVALID_QUANTITY")
    if quantity <= 0:
        raise AccountError("quantity must be positive", "INVALID_QUANTITY")
    return quantity


def _validate_non_negative_int(value: int, field_name: str) -> int:
    if not isinstance(value, int):
        raise AccountError(f"{field_name} must be an integer", "INVALID_VALUE")
    if value < 0:
        raise AccountError(f"{field_name} must be non-negative", "INVALID_VALUE")
    return value


def _validate_decimal(value: Decimal, field_name: str, non_negative: bool = True) -> Decimal:
    if not isinstance(value, Decimal):
        try:
            value = Decimal(str(value))
        except Exception as exc:
            raise AccountError(f"{field_name} must be a Decimal-compatible value", "INVALID_VALUE") from exc
    if non_negative and value < Decimal("0"):
        raise AccountError(f"{field_name} must be non-negative", "INVALID_VALUE")
    return value


def _validate_price_quantity_consistency(unit_price: Decimal, quantity: int, total_amount: Decimal) -> None:
    expected = unit_price * Decimal(quantity)
    if expected != total_amount:
        raise AccountError(
            "total_amount must equal unit_price * quantity",
            "INVALID_TOTAL_AMOUNT",
        )