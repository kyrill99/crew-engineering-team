from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Callable, Dict


class PriceProviderError(Exception):
    """Domain-specific exception for price provider failures."""

    def __init__(self, message: str, code: str) -> None:
        self.message = str(message)
        self.code = str(code)
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def _to_decimal(value: object, field_name: str = "value") -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise PriceProviderError(
            f"{field_name} must be Decimal-compatible",
            "INVALID_VALUE",
        ) from exc


def _normalize_symbol(symbol: str) -> str:
    if not isinstance(symbol, str) or not symbol.strip():
        raise PriceProviderError("symbol must be a non-empty string", "INVALID_SYMBOL")
    return symbol.strip().upper()


@dataclass(frozen=True)
class PriceProvider:
    """
    Abstracts market price access behind a stable interface.

    Parameters
    ----------
    price_source:
        Callable that accepts a stock symbol and returns the current price.
        The callable may return Decimal, int, float, or str representations
        of a numeric price.
    """

    price_source: Callable[[str], object]

    def __post_init__(self) -> None:
        if not callable(self.price_source):
            raise PriceProviderError(
                "price_source must be callable",
                "INVALID_PRICE_SOURCE",
            )

    def get_share_price(self, symbol: str) -> Decimal:
        """
        Return the current share price for the given symbol as a Decimal.
        """
        normalized_symbol = _normalize_symbol(symbol)
        try:
            raw_price = self.price_source(normalized_symbol)
        except PriceProviderError:
            raise
        except Exception as exc:
            raise PriceProviderError(
                f"failed to retrieve price for {normalized_symbol}",
                "PRICE_LOOKUP_FAILED",
            ) from exc

        price = _to_decimal(raw_price, "price")
        if price <= Decimal("0"):
            raise PriceProviderError(
                f"price for {normalized_symbol} must be positive",
                "INVALID_PRICE",
            )

        return price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class FixedPriceProvider(PriceProvider):
    """
    Test implementation returning fixed prices for supported symbols.
    """

    DEFAULT_PRICES: Dict[str, Decimal] = {
        "AAPL": Decimal("190.00"),
        "TSLA": Decimal("250.00"),
        "GOOGL": Decimal("140.00"),
    }

    def __init__(self, prices: Dict[str, object] | None = None) -> None:
        resolved: Dict[str, Decimal] = {
            symbol: _to_decimal(price, f"price[{symbol}]")
            for symbol, price in (prices or self.DEFAULT_PRICES).items()
        }

        def _source(symbol: str) -> Decimal:
            normalized = _normalize_symbol(symbol)
            if normalized not in resolved:
                raise PriceProviderError(
                    f"unsupported symbol: {normalized}",
                    "UNKNOWN_SYMBOL",
                )
            return resolved[normalized]

        super().__init__(price_source=_source)


def default_price_source(symbol: str) -> Decimal:
    """
    Convenience default test price source for AAPL, TSLA, and GOOGL.
    """
    return FixedPriceProvider().get_share_price(symbol)


__all__ = [
    "PriceProvider",
    "PriceProviderError",
    "FixedPriceProvider",
    "default_price_source",
]