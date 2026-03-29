from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable, Dict, List, Optional

try:
    from price_provider import PriceProvider, PriceProviderError, FixedPriceProvider, default_price_source
except Exception:  # pragma: no cover
    PriceProvider = None  # type: ignore
    PriceProviderError = Exception  # type: ignore
    FixedPriceProvider = None  # type: ignore
    default_price_source = None  # type: ignore

try:
    from account_state import AccountState, AccountError, TransactionType
except Exception:  # pragma: no cover
    from __main__ import AccountState, AccountError, TransactionType  # type: ignore


def _to_decimal(value: object, field_name: str = "value") -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise AccountError(f"{field_name} must be Decimal-compatible", "INVALID_VALUE") from exc


def _normalize_decimal(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PortfolioService:
    """
    Computes derived portfolio views from an AccountState.

    The service is intentionally read-only: it never mutates account state.
    It relies on a price provider callable or object to obtain current market prices.
    """

    price_provider: Callable[[str], object] = default_price_source if default_price_source is not None else None

    def __post_init__(self) -> None:
        if self.price_provider is None or not callable(self.price_provider):
            raise AccountError("price_provider must be callable", "INVALID_PRICE_PROVIDER")

    def _get_share_price(self, symbol: str) -> Decimal:
        if hasattr(self.price_provider, "get_share_price"):
            raw_price = self.price_provider.get_share_price(symbol)  # type: ignore[attr-defined]
        else:
            raw_price = self.price_provider(symbol)
        price = _to_decimal(raw_price, "price")
        if price <= Decimal("0"):
            raise AccountError(f"price for {symbol} must be positive", "INVALID_PRICE")
        return _normalize_decimal(price)

    def calculate_holdings_value(self, state: AccountState) -> Decimal:
        self._validate_state(state)
        total = Decimal("0")
        for symbol, quantity in state.holdings.items():
            if quantity <= 0:
                continue
            total += self._get_share_price(symbol) * Decimal(quantity)
        return _normalize_decimal(total)

    def calculate_portfolio_value(self, state: AccountState) -> Decimal:
        self._validate_state(state)
        total = _to_decimal(state.cash_balance, "cash_balance")
        total += self.calculate_holdings_value(state)
        return _normalize_decimal(total)

    def calculate_profit_loss(self, state: AccountState) -> Decimal:
        self._validate_state(state)
        profit_loss = self.calculate_portfolio_value(state) - _to_decimal(
            state.initial_deposit_basis, "initial_deposit_basis"
        )
        return _normalize_decimal(profit_loss)

    def build_holdings_report(self, state: AccountState) -> List[Dict[str, Any]]:
        self._validate_state(state)
        report: List[Dict[str, Any]] = []
        for symbol in sorted(state.holdings.keys()):
            quantity = int(state.holdings[symbol])
            if quantity <= 0:
                continue
            unit_price = self._get_share_price(symbol)
            market_value = _normalize_decimal(unit_price * Decimal(quantity))
            report.append(
                {
                    "symbol": symbol,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "market_value": market_value,
                }
            )
        return report

    def _validate_state(self, state: AccountState) -> None:
        if not isinstance(state, AccountState):
            raise AccountError("state must be an AccountState instance", "INVALID_STATE")


__all__ = [
    "PortfolioService",
]