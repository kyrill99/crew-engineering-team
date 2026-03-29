from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


__all__ = [
    "AccountError",
    "InsufficientFundsError",
    "InsufficientHoldingsError",
    "UnknownSymbolError",
    "Transaction",
    "Position",
    "get_share_price",
    "Account",
]


class AccountError(Exception):
    """Base class for account-related failures."""


class InsufficientFundsError(AccountError):
    """Raised when there are not enough funds to complete an operation."""


class InsufficientHoldingsError(AccountError):
    """Raised when there are not enough shares to complete an operation."""


class UnknownSymbolError(AccountError):
    """Raised when a requested symbol has no known price."""


_PRICE_TABLE: Dict[str, float] = {
    "AAPL": 190.0,
    "TSLA": 250.0,
    "GOOGL": 140.0,
}


def get_share_price(symbol: str) -> float:
    if not isinstance(symbol, str) or not symbol.strip():
        raise UnknownSymbolError("Symbol must be a non-empty string.")
    key = symbol.strip().upper()
    try:
        return float(_PRICE_TABLE[key])
    except KeyError as exc:
        raise UnknownSymbolError(f"Unknown symbol: {symbol}") from exc


@dataclass(frozen=True)
class Transaction:
    timestamp: datetime
    transaction_type: str
    amount: float
    symbol: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    cash_balance_after: float = 0.0
    holdings_after: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "transaction_type": self.transaction_type,
            "amount": self.amount,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "price": self.price,
            "cash_balance_after": self.cash_balance_after,
            "holdings_after": dict(self.holdings_after),
        }


@dataclass(frozen=True)
class Position:
    symbol: str
    quantity: int
    current_price: float
    market_value: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "current_price": self.current_price,
            "market_value": self.market_value,
        }


class Account:
    def __init__(self, account_id: str, owner_name: str | None = None) -> None:
        if not isinstance(account_id, str) or not account_id.strip():
            raise ValueError("account_id must be a non-empty string.")
        self.account_id: str = account_id
        self.owner_name: str | None = owner_name
        self.cash_balance: float = 0.0
        self.initial_deposit: float = 0.0
        self.holdings: Dict[str, int] = {}
        self.transactions: List[Transaction] = []
        self._total_deposits: float = 0.0
        self._total_withdrawals: float = 0.0

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _validate_amount(self, amount: float) -> None:
        if not isinstance(amount, (int, float)) or isinstance(amount, bool) or amount <= 0:
            raise ValueError("amount must be greater than zero.")

    def _validate_quantity(self, quantity: int) -> None:
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
            raise ValueError("quantity must be a positive integer.")

    def _record_transaction(self, transaction: Transaction) -> None:
        self.transactions.append(transaction)

    def _get_holding_quantity(self, symbol: str) -> int:
        return self.holdings.get(symbol.upper(), 0)

    def deposit(self, amount: float) -> None:
        self._validate_amount(amount)
        amount = float(amount)
        self.cash_balance += amount
        self._total_deposits += amount
        if self.initial_deposit == 0.0:
            self.initial_deposit = amount
        txn = Transaction(
            timestamp=self._now(),
            transaction_type="deposit",
            amount=amount,
            cash_balance_after=self.cash_balance,
            holdings_after=self.get_holdings(),
        )
        self._record_transaction(txn)

    def withdraw(self, amount: float) -> None:
        self._validate_amount(amount)
        amount = float(amount)
        if amount > self.cash_balance:
            raise InsufficientFundsError("Withdrawal would result in negative cash balance.")
        self.cash_balance -= amount
        self._total_withdrawals += amount
        txn = Transaction(
            timestamp=self._now(),
            transaction_type="withdrawal",
            amount=amount,
            cash_balance_after=self.cash_balance,
            holdings_after=self.get_holdings(),
        )
        self._record_transaction(txn)

    def buy_shares(self, symbol: str, quantity: int) -> None:
        self._validate_quantity(quantity)
        symbol_key = symbol.strip().upper() if isinstance(symbol, str) else ""
        price = get_share_price(symbol_key)
        total_cost = price * quantity
        if total_cost > self.cash_balance:
            raise InsufficientFundsError("Not enough cash to buy shares.")
        self.cash_balance -= total_cost
        self.holdings[symbol_key] = self.holdings.get(symbol_key, 0) + quantity
        txn = Transaction(
            timestamp=self._now(),
            transaction_type="buy",
            amount=total_cost,
            symbol=symbol_key,
            quantity=quantity,
            price=price,
            cash_balance_after=self.cash_balance,
            holdings_after=self.get_holdings(),
        )
        self._record_transaction(txn)

    def sell_shares(self, symbol: str, quantity: int) -> None:
        self._validate_quantity(quantity)
        symbol_key = symbol.strip().upper() if isinstance(symbol, str) else ""
        owned = self.holdings.get(symbol_key, 0)
        if owned < quantity:
            raise InsufficientHoldingsError("Not enough shares to sell.")
        price = get_share_price(symbol_key)
        proceeds = price * quantity
        self.cash_balance += proceeds
        remaining = owned - quantity
        if remaining > 0:
            self.holdings[symbol_key] = remaining
        else:
            self.holdings.pop(symbol_key, None)
        txn = Transaction(
            timestamp=self._now(),
            transaction_type="sell",
            amount=proceeds,
            symbol=symbol_key,
            quantity=quantity,
            price=price,
            cash_balance_after=self.cash_balance,
            holdings_after=self.get_holdings(),
        )
        self._record_transaction(txn)

    def get_holdings(self) -> Dict[str, int]:
        return dict(self.holdings)

    def get_cash_balance(self) -> float:
        return float(self.cash_balance)

    def get_portfolio_value(self) -> float:
        total = self.cash_balance
        for symbol, quantity in self.holdings.items():
            price = get_share_price(symbol)
            total += price * quantity
        return float(total)

    def get_profit_loss(self) -> float:
        return float(self.get_portfolio_value() - (self._total_deposits - self._total_withdrawals))

    def get_transaction_history(self) -> List[Transaction]:
        return list(self.transactions)

    def get_positions(self) -> List[Position]:
        positions: List[Position] = []
        for symbol, quantity in self.holdings.items():
            price = get_share_price(symbol)
            positions.append(
                Position(
                    symbol=symbol,
                    quantity=quantity,
                    current_price=price,
                    market_value=price * quantity,
                )
            )
        return positions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "owner_name": self.owner_name,
            "cash_balance": self.get_cash_balance(),
            "holdings": self.get_holdings(),
            "portfolio_value": self.get_portfolio_value(),
            "profit_loss": self.get_profit_loss(),
            "transactions": [txn.to_dict() for txn in self.transactions],
            "positions": [position.to_dict() for position in self.get_positions()],
            "initial_deposit": self.initial_deposit,
        }