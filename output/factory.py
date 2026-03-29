from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

try:
    from account import AccountService, AccountError
except Exception:
    try:
        from trading_account import AccountService, AccountError
    except Exception:
        from typing import Callable, Dict, List
        from datetime import datetime
        from enum import Enum
        from dataclasses import dataclass, field

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

            def __post_init__(self) -> None:
                self.account_id = _validate_account_id(self.account_id)
                self.cash_balance = Decimal("0")
                self.initial_deposit_basis = Decimal("0")
                self.holdings = {}
                self.transactions = []

        class AccountService:
            def __init__(self, price_provider=None) -> None:
                self._price_provider = price_provider or get_share_price
                self._account = None

            def create_account(self, account_id: str) -> None:
                if self._account is not None:
                    raise AccountError("account already exists", "ACCOUNT_ALREADY_EXISTS")
                self._account = AccountState(account_id=account_id)

            def _require_account(self) -> AccountState:
                if self._account is None:
                    raise AccountError("account has not been created", "ACCOUNT_NOT_FOUND")
                return self._account

from price_provider import FixedPriceProvider, PriceProvider, PriceProviderError


class AccountServiceFactory:
    """
    Factory for wiring AccountService instances.

    This centralizes dependency assembly so application code can easily create:
    - a service with the built-in fixed test prices
    - a service backed by a custom injected price provider
    """

    def create_with_fixed_prices(self, account_id: str) -> AccountService:
        """
        Create a fully wired AccountService using the fixed test price provider.
        """
        provider = FixedPriceProvider()
        service = AccountService(price_provider=provider.get_share_price)
        service.create_account(account_id)
        return service

    def create_with_price_provider(self, account_id: str, price_provider: PriceProvider) -> AccountService:
        """
        Create a fully wired AccountService using the supplied PriceProvider.
        """
        if price_provider is None:
            raise AccountError("price_provider must not be None", "INVALID_PRICE_PROVIDER")

        if not hasattr(price_provider, "get_share_price") or not callable(price_provider.get_share_price):
            raise AccountError("price_provider must provide a callable get_share_price method", "INVALID_PRICE_PROVIDER")

        service = AccountService(price_provider=price_provider.get_share_price)
        service.create_account(account_id)
        return service


__all__ = [
    "AccountServiceFactory",
]