from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Callable, Dict, List, Optional


class AccountError(Exception):
    """
    Domain-specific exception for invalid account operations.
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


def _validate_decimal(value: Decimal, field_name: str, non_negative: bool = True) -> Decimal:
    if not isinstance(value, Decimal):
        try:
            value = Decimal(str(value))
        except Exception as exc:
            raise AccountError(f"{field_name} must be a Decimal-compatible value", "INVALID_VALUE") from exc
    if non_negative and value < Decimal("0"):
        raise AccountError(f"{field_name} must be non-negative", "INVALID_VALUE")
    return value


def _validate_non_negative_int(value: int, field_name: str) -> int:
    if not isinstance(value, int):
        raise AccountError(f"{field_name} must be an integer", "INVALID_VALUE")
    if value < 0:
        raise AccountError(f"{field_name} must be non-negative", "INVALID_VALUE")
    return value


def _validate_price_quantity_consistency(unit_price: Decimal, quantity: int, total_amount: Decimal) -> None:
    if unit_price * Decimal(quantity) != total_amount:
        raise AccountError("total_amount must equal unit_price * quantity", "INVALID_TOTAL_AMOUNT")


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
        tx = Transaction(TransactionType.DEPOSIT, timestamp, self.account_id, amount=amount, post_cash_balance=self.cash_balance)
        self.transactions.append(tx)
        return tx

    def apply_withdrawal(self, amount: Decimal, timestamp: datetime) -> Transaction:
        amount = _validate_decimal(amount, "amount")
        timestamp = _validate_timestamp(timestamp)
        if amount > self.cash_balance:
            raise AccountError("withdrawal would leave account with negative cash balance", "INSUFFICIENT_FUNDS")
        self.cash_balance -= amount
        tx = Transaction(TransactionType.WITHDRAWAL, timestamp, self.account_id, amount=amount, post_cash_balance=self.cash_balance)
        self.transactions.append(tx)
        return tx

    def apply_buy(self, symbol: str, quantity: int, unit_price: Decimal, timestamp: datetime) -> Transaction:
        symbol = _validate_symbol(symbol)
        quantity = _validate_quantity(quantity)
        unit_price = _validate_decimal(unit_price, "unit_price")
        timestamp = _validate_timestamp(timestamp)
        total_amount = unit_price * Decimal(quantity)
        if total_amount > self.cash_balance:
            raise AccountError("buy would exceed available cash balance", "INSUFFICIENT_FUNDS")
        self.cash_balance -= total_amount
        post_holding_quantity = self.holdings.get(symbol, 0) + quantity
        self.holdings[symbol] = post_holding_quantity
        tx = Transaction(
            TransactionType.BUY,
            timestamp,
            self.account_id,
            symbol=symbol,
            quantity=quantity,
            unit_price=unit_price,
            total_amount=total_amount,
            post_cash_balance=self.cash_balance,
            post_holding_quantity=post_holding_quantity,
        )
        self.transactions.append(tx)
        return tx

    def apply_sell(self, symbol: str, quantity: int, unit_price: Decimal, timestamp: datetime) -> Transaction:
        symbol = _validate_symbol(symbol)
        quantity = _validate_quantity(quantity)
        unit_price = _validate_decimal(unit_price, "unit_price")
        timestamp = _validate_timestamp(timestamp)
        current_quantity = self.holdings.get(symbol, 0)
        if quantity > current_quantity:
            raise AccountError("sell would exceed current holdings", "INSUFFICIENT_HOLDINGS")
        total_amount = unit_price * Decimal(quantity)
        post_holding_quantity = current_quantity - quantity
        if post_holding_quantity == 0:
            self.holdings.pop(symbol, None)
        else:
            self.holdings[symbol] = post_holding_quantity
        self.cash_balance += total_amount
        tx = Transaction(
            TransactionType.SELL,
            timestamp,
            self.account_id,
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


class AccountService:
    """
    Application-facing service that orchestrates account creation, deposits,
    withdrawals, buy/sell operations, and read-only reporting.
    """

    def __init__(self, price_provider: Optional[Callable[[str], Decimal]] = None) -> None:
        self._price_provider = price_provider or get_share_price
        self._account: Optional[AccountState] = None

    def create_account(self, account_id: str) -> None:
        if self._account is not None:
            raise AccountError("account already exists", "ACCOUNT_ALREADY_EXISTS")
        self._account = AccountState(account_id=account_id)

    def deposit(self, amount: Decimal) -> Transaction:
        state = self._require_account()
        tx = state.apply_deposit(_validate_decimal(amount, "amount"), datetime.utcnow())
        return tx

    def withdraw(self, amount: Decimal) -> Transaction:
        state = self._require_account()
        amount = _validate_decimal(amount, "amount")
        return state.apply_withdrawal(amount, datetime.utcnow())

    def buy_shares(self, symbol: str, quantity: int) -> Transaction:
        state = self._require_account()
        symbol = _validate_symbol(symbol)
        quantity = _validate_quantity(quantity)
        unit_price = self._get_share_price(symbol)
        total_amount = unit_price * Decimal(quantity)
        if total_amount > state.cash_balance:
            raise AccountError("buy would exceed available cash balance", "INSUFFICIENT_FUNDS")
        return state.apply_buy(symbol, quantity, unit_price, datetime.utcnow())

    def sell_shares(self, symbol: str, quantity: int) -> Transaction:
        state = self._require_account()
        symbol = _validate_symbol(symbol)
        quantity = _validate_quantity(quantity)
        held = state.get_holding_quantity(symbol)
        if quantity > held:
            raise AccountError("sell would exceed current holdings", "INSUFFICIENT_HOLDINGS")
        unit_price = self._get_share_price(symbol)
        return state.apply_sell(symbol, quantity, unit_price, datetime.utcnow())

    def get_holdings(self) -> Dict[str, int]:
        state = self._require_account()
        return state.get_holdings()

    def get_portfolio_value(self) -> Decimal:
        state = self._require_account()
        return state.get_portfolio_value(price_provider=self._price_provider)

    def get_profit_loss(self) -> Decimal:
        state = self._require_account()
        return state.get_profit_loss(price_provider=self._price_provider)

    def list_transactions(self) -> List[Transaction]:
        state = self._require_account()
        return state.get_transactions()

    def _get_share_price(self, symbol: str) -> Decimal:
        price = self._price_provider(symbol)
        if not isinstance(price, Decimal):
            price = Decimal(str(price))
        if price <= Decimal("0"):
            raise AccountError("share price must be positive", "INVALID_PRICE")
        return price

    def _require_account(self) -> AccountState:
        if self._account is None:
            raise AccountError("account has not been created", "ACCOUNT_NOT_FOUND")
        return self._account


__all__ = [
    "AccountError",
    "AccountService",
    "AccountState",
    "Transaction",
    "TransactionType",
    "get_share_price",
]