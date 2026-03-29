from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Callable


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


def get_share_price(symbol: str) -> Decimal:
    symbol = _validate_symbol(symbol)
    prices = {
        "AAPL": Decimal("190.00"),
        "TSLA": Decimal("250.00"),
        "GOOGL": Decimal("140.00"),
    }
    try:
        return prices[symbol]
    except KeyError as exc:
        raise AccountError(f"unsupported symbol: {symbol}", "UNKNOWN_SYMBOL") from exc


@dataclass
class AccountState:
    """
    Encapsulates mutable account state for a trading simulation account.

    The class assumes that external validation has already occurred for business-rule
    checks such as sufficient funds and sufficient holdings, but it still validates
    basic types/format for safety.
    """

    account_id: str
    cash_balance: Decimal = field(init=False, default=Decimal("0"))
    initial_deposit_basis: Decimal = field(init=False, default=Decimal("0"))
    holdings: Dict[str, int] = field(init=False, default_factory=dict)
    transactions: List[Transaction] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        self.account_id = _validate_account_id(self.account_id)
        self.cash_balance = Decimal("0")
        self.initial_deposit_basis = Decimal("0")
        self.holdings = {}
        self.transactions = []
        self.transactions.append(
            Transaction(
                transaction_type=TransactionType.ACCOUNT_CREATED,
                timestamp=datetime.utcnow(),
                account_id=self.account_id,
                metadata={"source": "AccountState.__post_init__"},
            )
        )

    def apply_deposit(self, amount: Decimal, timestamp: datetime) -> Transaction:
        amount = _validate_decimal(amount, "amount")
        timestamp = _validate_timestamp(timestamp)
        self.cash_balance += amount
        self.initial_deposit_basis += amount
        tx = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            timestamp=timestamp,
            account_id=self.account_id,
            amount=amount,
            post_cash_balance=self.cash_balance,
        )
        self.transactions.append(tx)
        return tx

    def apply_withdrawal(self, amount: Decimal, timestamp: datetime) -> Transaction:
        amount = _validate_decimal(amount, "amount")
        timestamp = _validate_timestamp(timestamp)
        if amount > self.cash_balance:
            raise AccountError(
                "withdrawal would leave account with negative cash balance",
                "INSUFFICIENT_FUNDS",
            )
        self.cash_balance -= amount
        tx = Transaction(
            transaction_type=TransactionType.WITHDRAWAL,
            timestamp=timestamp,
            account_id=self.account_id,
            amount=amount,
            post_cash_balance=self.cash_balance,
        )
        self.transactions.append(tx)
        return tx

    def apply_buy(
        self, symbol: str, quantity: int, unit_price: Decimal, timestamp: datetime
    ) -> Transaction:
        symbol = _validate_symbol(symbol)
        quantity = _validate_quantity(quantity)
        unit_price = _validate_decimal(unit_price, "unit_price")
        timestamp = _validate_timestamp(timestamp)
        total_amount = unit_price * Decimal(quantity)
        if total_amount > self.cash_balance:
            raise AccountError(
                "buy would exceed available cash balance",
                "INSUFFICIENT_FUNDS",
            )
        self.cash_balance -= total_amount
        post_holding_quantity = self.holdings.get(symbol, 0) + quantity
        self.holdings[symbol] = post_holding_quantity
        tx = Transaction(
            transaction_type=TransactionType.BUY,
            timestamp=timestamp,
            account_id=self.account_id,
            symbol=symbol,
            quantity=quantity,
            unit_price=unit_price,
            total_amount=total_amount,
            post_cash_balance=self.cash_balance,
            post_holding_quantity=post_holding_quantity,
        )
        self.transactions.append(tx)
        return tx

    def apply_sell(
        self, symbol: str, quantity: int, unit_price: Decimal, timestamp: datetime
    ) -> Transaction:
        symbol = _validate_symbol(symbol)
        quantity = _validate_quantity(quantity)
        unit_price = _validate_decimal(unit_price, "unit_price")
        timestamp = _validate_timestamp(timestamp)
        current_quantity = self.holdings.get(symbol, 0)
        if quantity > current_quantity:
            raise AccountError(
                "sell would exceed current holdings",
                "INSUFFICIENT_HOLDINGS",
            )
        total_amount = unit_price * Decimal(quantity)
        post_holding_quantity = current_quantity - quantity
        if post_holding_quantity == 0:
            self.holdings.pop(symbol, None)
        else:
            self.holdings[symbol] = post_holding_quantity
        self.cash_balance += total_amount
        tx = Transaction(
            transaction_type=TransactionType.SELL,
            timestamp=timestamp,
            account_id=self.account_id,
            symbol=symbol,
            quantity=quantity,
            unit_price=unit_price,
            total_amount=total_amount,
            post_cash_balance=self.cash_balance,
            post_holding_quantity=post_holding_quantity,
        )
        self.transactions.append(tx)
        return tx

    def get_holding_quantity(self, symbol: str) -> int:
        symbol = _validate_symbol(symbol)
        return int(self.holdings.get(symbol, 0))

    def get_holdings(self) -> Dict[str, int]:
        return dict(sorted(self.holdings.items()))

    def get_transactions(self) -> List[Transaction]:
        return list(self.transactions)

    def get_portfolio_value(self, price_provider: Optional[Callable[[str], Decimal]] = None) -> Decimal:
        provider = price_provider or get_share_price
        total = self.cash_balance
        for symbol, quantity in self.holdings.items():
            price = provider(symbol)
            if not isinstance(price, Decimal):
                price = Decimal(str(price))
            total += price * Decimal(quantity)
        return total

    def get_profit_loss(self, price_provider: Optional[Callable[[str], Decimal]] = None) -> Decimal:
        return self.get_portfolio_value(price_provider=price_provider) - self.initial_deposit_basis

    def get_holdings_snapshot(self) -> Dict[str, int]:
        return self.get_holdings()

    def list_transactions(self) -> List[Transaction]:
        return self.get_transactions()


__all__ = [
    "AccountError",
    "AccountState",
    "Transaction",
    "TransactionType",
    "get_share_price",
]