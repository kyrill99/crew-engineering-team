from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Callable, Any


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


class AccountValidator:
    """
    Centralizes input and business-rule validation for trading account operations.

    This validator is intentionally focused on validation only. It does not mutate
    state and is safe to reuse across account service implementations.
    """

    INVALID_AMOUNT_CODE = "INVALID_AMOUNT"
    INVALID_QUANTITY_CODE = "INVALID_QUANTITY"
    SYMBOL_PRICE_UNAVAILABLE_CODE = "SYMBOL_PRICE_UNAVAILABLE"
    INSUFFICIENT_CASH_CODE = "INSUFFICIENT_CASH"
    INSUFFICIENT_SHARES_CODE = "INSUFFICIENT_SHARES"

    def validate_positive_amount(self, amount: Decimal) -> None:
        """
        Ensure the provided monetary amount is strictly positive.
        """
        self._ensure_decimal(amount, self.INVALID_AMOUNT_CODE, "Amount must be a Decimal value.")
        if amount <= Decimal("0"):
            raise AccountError("Amount must be greater than zero.", self.INVALID_AMOUNT_CODE)

    def validate_positive_integer_quantity(self, quantity: int) -> None:
        """
        Ensure the provided share quantity is a positive integer.
        """
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise AccountError("Quantity must be an integer.", self.INVALID_QUANTITY_CODE)
        if quantity <= 0:
            raise AccountError("Quantity must be greater than zero.", self.INVALID_QUANTITY_CODE)

    def validate_symbol_price_available(
        self,
        symbol: str,
        price_lookup: Callable[[str], Decimal],
    ) -> Decimal:
        """
        Ensure a symbol resolves to a valid current share price.

        Returns the price if available and valid.
        """
        if not isinstance(symbol, str) or not symbol.strip():
            raise AccountError("Symbol must be a non-empty string.", self.SYMBOL_PRICE_UNAVAILABLE_CODE)

        normalized_symbol = symbol.strip().upper()

        try:
            price = price_lookup(normalized_symbol)
        except Exception as exc:
            raise AccountError(
                f"Price lookup failed for symbol '{normalized_symbol}'.",
                self.SYMBOL_PRICE_UNAVAILABLE_CODE,
            ) from exc

        self._ensure_decimal(
            price,
            self.SYMBOL_PRICE_UNAVAILABLE_CODE,
            f"Price for symbol '{normalized_symbol}' must be a Decimal value.",
        )

        if price <= Decimal("0"):
            raise AccountError(
                f"Price for symbol '{normalized_symbol}' must be greater than zero.",
                self.SYMBOL_PRICE_UNAVAILABLE_CODE,
            )

        return price

    def validate_sufficient_cash(self, cash_balance: Decimal, required: Decimal) -> None:
        """
        Ensure the cash balance is sufficient to cover a required amount.
        """
        self._ensure_decimal(cash_balance, self.INSUFFICIENT_CASH_CODE, "Cash balance must be a Decimal value.")
        self._ensure_decimal(required, self.INSUFFICIENT_CASH_CODE, "Required cash must be a Decimal value.")

        if cash_balance < Decimal("0"):
            raise AccountError("Cash balance cannot be negative.", self.INSUFFICIENT_CASH_CODE)
        if required < Decimal("0"):
            raise AccountError("Required cash cannot be negative.", self.INSUFFICIENT_CASH_CODE)
        if cash_balance < required:
            raise AccountError(
                "Insufficient cash to complete the operation.",
                self.INSUFFICIENT_CASH_CODE,
            )

    def validate_sufficient_shares(self, held_quantity: int, requested_quantity: int) -> None:
        """
        Ensure the user holds at least the requested number of shares.
        """
        if isinstance(held_quantity, bool) or not isinstance(held_quantity, int):
            raise AccountError("Held quantity must be an integer.", self.INSUFFICIENT_SHARES_CODE)
        if isinstance(requested_quantity, bool) or not isinstance(requested_quantity, int):
            raise AccountError("Requested quantity must be an integer.", self.INSUFFICIENT_SHARES_CODE)

        if held_quantity < 0:
            raise AccountError("Held quantity cannot be negative.", self.INSUFFICIENT_SHARES_CODE)
        if requested_quantity < 0:
            raise AccountError("Requested quantity cannot be negative.", self.INSUFFICIENT_SHARES_CODE)
        if held_quantity < requested_quantity:
            raise AccountError(
                "Insufficient shares to complete the operation.",
                self.INSUFFICIENT_SHARES_CODE,
            )

    @staticmethod
    def _ensure_decimal(value: Any, code: str, message: str) -> None:
        if not isinstance(value, Decimal):
            raise AccountError(message, code)
        try:
            _ = value.is_finite()
        except (InvalidOperation, AttributeError) as exc:
            raise AccountError(message, code) from exc