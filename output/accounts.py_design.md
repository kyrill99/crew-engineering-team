# `accounts.py` — Detailed Module Design

This module implements a self-contained account management system for a trading simulation platform.

It provides:

- account creation
- cash deposits and withdrawals
- share buys and sells
- holdings and transaction history
- portfolio value calculation
- profit/loss reporting
- validation to prevent invalid balances or trades

The module is designed so it can be used directly in tests or from a simple UI with no external dependencies.

---

## Module-level responsibilities

The `accounts.py` module should contain:

1. A **share price lookup function** `get_share_price(symbol)`  
   - Uses a built-in test price table for:
     - `AAPL`
     - `TSLA`
     - `GOOGL`

2. A single main class: **`Account`**  
   - Represents one trading simulation account.
   - Stores cash balance, share holdings, and transaction history.
   - Exposes methods for deposits, withdrawals, trades, and reporting.

3. Optional internal helper types for clarity:
   - transaction records
   - exception classes for validation failures

The implementation should remain fully self-contained within one Python file.

---

# Public API

## 1) `get_share_price(symbol: str) -> float`

### Purpose
Returns the current simulated market price for a share symbol.

### Behavior
- Accepts a ticker symbol like `"AAPL"`.
- Returns a fixed price for supported symbols in the test implementation.
- Raises an error for unknown symbols.

### Suggested test prices
A simple built-in price map can be used:

- `AAPL` → `190.0`
- `TSLA` → `250.0`
- `GOOGL` → `140.0`

These values may be changed in tests if needed, but the function must exist and be usable by `Account`.

### Signature
```python
def get_share_price(symbol: str) -> float:
    ...
```

---

## 2) `class Account`

Represents a trading simulation user account.

### Core concept
The account tracks:

- `cash_balance`
- holdings by symbol
- transaction history
- initial deposit amount
- realized and unrealized P/L

The account should start with zero cash and no holdings.

---

# `Account` class design

## Constructor

### `__init__(self, account_id: str, owner_name: str | None = None) -> None`

### Purpose
Creates a new account instance.

### Parameters
- `account_id`: unique account identifier
- `owner_name`: optional display name for the user

### Initial state
- cash balance = `0.0`
- holdings = empty
- transaction history = empty
- initial deposit = `0.0`
- no realized trades yet

### Suggested attributes
- `self.account_id: str`
- `self.owner_name: str | None`
- `self.cash_balance: float`
- `self.initial_deposit: float`
- `self.holdings: dict[str, int]`
- `self.transactions: list[Transaction]`

---

## Account methods

---

### `deposit(self, amount: float) -> None`

### Purpose
Adds cash to the account.

### Validation
- `amount` must be greater than zero.

### Effects
- `cash_balance += amount`
- if this is the first deposit, track it as part of the initial funding baseline
- append a deposit transaction to history

### Errors
- raise `ValueError` if `amount <= 0`

### Notes
The system should treat deposits as available trading capital.

---

### `withdraw(self, amount: float) -> None`

### Purpose
Removes cash from the account.

### Validation
- `amount` must be greater than zero
- withdrawal must not reduce cash balance below zero

### Effects
- `cash_balance -= amount`
- append a withdrawal transaction

### Errors
- raise `ValueError` if `amount <= 0`
- raise `InsufficientFundsError` if withdrawal would make balance negative

---

### `buy_shares(self, symbol: str, quantity: int) -> None`

### Purpose
Records that the user bought shares of a symbol.

### Parameters
- `symbol`: share ticker
- `quantity`: number of shares bought

### Behavior
- Retrieves the current market price using `get_share_price(symbol)`
- Computes total cost = `price * quantity`
- Verifies the user has enough cash to pay for the purchase
- Reduces cash balance by total cost
- Increases holdings for the symbol
- Records transaction history

### Validation
- `quantity` must be a positive integer
- symbol must be supported by `get_share_price`
- account must have enough cash

### Errors
- `ValueError` for invalid quantity
- `UnknownSymbolError` if price lookup fails
- `InsufficientFundsError` if the account cannot afford the shares

### Example
If price of `AAPL` is `190.0` and quantity is `2`, cost is `380.0`.

---

### `sell_shares(self, symbol: str, quantity: int) -> None`

### Purpose
Records that the user sold shares of a symbol.

### Parameters
- `symbol`: share ticker
- `quantity`: number of shares sold

### Behavior
- Verifies the account owns enough shares of the symbol
- Retrieves current price using `get_share_price(symbol)`
- Computes sale proceeds = `price * quantity`
- Increases cash balance by sale proceeds
- Decreases holdings for the symbol
- Removes the symbol from holdings if quantity goes to zero
- Records transaction history

### Validation
- `quantity` must be a positive integer
- account must own at least that many shares

### Errors
- `ValueError` for invalid quantity
- `InsufficientHoldingsError` if selling more shares than owned
- `UnknownSymbolError` if the symbol price cannot be found

---

### `get_holdings(self) -> dict[str, int]`

### Purpose
Returns the current share holdings.

### Behavior
- Returns a snapshot of holdings as a dictionary
- Should not expose internal mutable state directly

### Example return
```python
{"AAPL": 5, "TSLA": 2}
```

### Notes
This should represent the holdings “at the current point in time.”

### Recommended implementation detail
Return a shallow copy.

---

### `get_cash_balance(self) -> float`

### Purpose
Returns current cash balance.

### Notes
Useful for UI and tests.

### Signature
```python
def get_cash_balance(self) -> float:
    ...
```

---

### `get_portfolio_value(self) -> float`

### Purpose
Calculates total current portfolio value.

### Formula
```text
portfolio_value = cash_balance + sum(quantity * current_share_price)
```

Where each share price is fetched using `get_share_price(symbol)`.

### Notes
- Includes both cash and current market value of all shares held
- Uses latest simulated prices

### Errors
- If a symbol in holdings no longer has a known price, the method should raise `UnknownSymbolError`

---

### `get_profit_loss(self) -> float`

### Purpose
Returns total profit or loss relative to the user’s initial deposit baseline.

### Suggested formula
```text
profit_loss = portfolio_value - total_net_contributed_cash
```

Where:
- `portfolio_value` is current cash + holdings market value
- `total_net_contributed_cash` = total deposits - total withdrawals

### Why this formula
This measures account performance relative to the amount of capital the user has net contributed.

### Notes
This works both when the user has open positions and when they only hold cash.

### Return value
- positive = profit
- negative = loss
- zero = break-even

---

### `get_transaction_history(self) -> list[Transaction]`

### Purpose
Returns the full list of transactions made by the user over time.

### Behavior
- Returns transactions in chronological order
- Should return a copy of the list to prevent accidental mutation

### Each transaction should include:
- timestamp
- transaction type
- symbol if applicable
- quantity if applicable
- price if applicable
- amount
- resulting cash balance
- resulting holdings snapshot

---

### `get_positions(self) -> list[Position]`

### Purpose
Returns current positions in a more structured form than raw holdings.

### Behavior
Each position should include:
- symbol
- quantity
- current price
- market value

This is useful for UI rendering.

### Notes
This method is optional but recommended for practical UI/test integration.

---

### `to_dict(self) -> dict[str, Any]`

### Purpose
Serializes the account state into a JSON-friendly structure.

### Includes
- account id
- owner name
- cash balance
- holdings
- portfolio value
- profit/loss
- transactions

### Notes
Useful for testing, debugging, and UI integration.

---

# Internal helper data structures

To keep the module clean and testable, it is recommended to use lightweight internal dataclasses.

---

## `Transaction` dataclass

Represents one account action.

### Suggested fields
```python
@dataclass
class Transaction:
    timestamp: datetime
    transaction_type: str   # "deposit", "withdrawal", "buy", "sell"
    amount: float
    symbol: str | None = None
    quantity: int | None = None
    price: float | None = None
    cash_balance_after: float = 0.0
    holdings_after: dict[str, int] = field(default_factory=dict)
```

### Purpose
Used for historical reporting and auditing.

---

## `Position` dataclass

Represents one current open holding.

### Suggested fields
```python
@dataclass
class Position:
    symbol: str
    quantity: int
    current_price: float
    market_value: float
```

### Purpose
Makes portfolio display easy and consistent.

---

# Custom exceptions

Custom exceptions are recommended so the caller can distinguish failures cleanly.

## `AccountError(Exception)`
Base class for account-related failures.

## `InsufficientFundsError(AccountError)`
Raised when:
- withdrawing too much cash
- buying shares without enough cash

## `InsufficientHoldingsError(AccountError)`
Raised when selling more shares than owned.

## `UnknownSymbolError(AccountError)`
Raised when a price lookup fails for an unsupported symbol.

---

# Required behavior details

## Account creation
- New account starts empty.
- No implicit deposit is made on account creation.

## Deposits
- Increase cash only.
- Do not affect holdings.

## Withdrawals
- Decrease cash only.
- Must never allow negative cash balance.

## Buying shares
- Uses current market price from `get_share_price(symbol)`.
- Deducts cash.
- Adds to holdings.
- Cannot exceed available cash.

## Selling shares
- Uses current market price from `get_share_price(symbol)`.
- Adds cash.
- Reduces holdings.
- Cannot exceed owned quantity.

## Portfolio value
- Current cash plus current market value of all holdings.

## Profit/loss
- Compare current portfolio value to net contributed cash.

## Holdings reporting
- Must reflect the exact current account state.
- Should not expose mutable internal collections directly.

## Transaction history
- Must list actions in time order.
- Should include enough data to reconstruct what happened.

---

# Recommended implementation details

## Data storage
Use standard Python structures:
- `dict[str, int]` for holdings
- `list[Transaction]` for history

## Time tracking
Use `datetime.utcnow()` or `datetime.now(timezone.utc)` for timestamps.

## Validation
Always validate:
- positive amounts
- positive quantities
- sufficient funds
- sufficient shares

## Precision
Because this is financial-like logic:
- use `float` for simplicity in this simulation
- for production, `Decimal` would be preferable
- but the design should remain simple unless strict precision is needed

---

# Suggested method signatures in full

```python
def get_share_price(symbol: str) -> float:
    ...

class Account:
    def __init__(self, account_id: str, owner_name: str | None = None) -> None:
        ...

    def deposit(self, amount: float) -> None:
        ...

    def withdraw(self, amount: float) -> None:
        ...

    def buy_shares(self, symbol: str, quantity: int) -> None:
        ...

    def sell_shares(self, symbol: str, quantity: int) -> None:
        ...

    def get_holdings(self) -> dict[str, int]:
        ...

    def get_cash_balance(self) -> float:
        ...

    def get_portfolio_value(self) -> float:
        ...

    def get_profit_loss(self) -> float:
        ...

    def get_transaction_history(self) -> list[Transaction]:
        ...

    def get_positions(self) -> list[Position]:
        ...

    def to_dict(self) -> dict[str, Any]:
        ...
```

---

# Suggested internal helpers

The module may also include private helper methods on `Account` to keep logic clean:

```python
def _validate_amount(self, amount: float) -> None:
    ...

def _validate_quantity(self, quantity: int) -> None:
    ...

def _record_transaction(self, transaction: Transaction) -> None:
    ...

def _get_holding_quantity(self, symbol: str) -> int:
    ...
```

These helpers should not be part of the external API.

---

# Example usage flow

1. Create account
2. Deposit cash
3. Buy shares
4. Sell shares
5. Withdraw some cash
6. Query holdings, value, and profit/loss
7. Inspect transaction history

Example sequence:

- `Account("ACC001", "Alice")`
- `deposit(10000)`
- `buy_shares("AAPL", 10)`
- `sell_shares("AAPL", 3)`
- `withdraw(500)`
- `get_holdings()`
- `get_portfolio_value()`
- `get_profit_loss()`
- `get_transaction_history()`

---

# Expected error conditions

The module must explicitly reject invalid actions:

- negative or zero deposit
- negative or zero withdrawal
- withdrawal that causes negative balance
- negative or zero share quantity
- buy shares without enough cash
- sell shares not owned
- sell more than owned
- unknown stock symbol

---

# Design summary

This module should provide a simple but complete account abstraction for a trading simulator.

## Minimal required surface
- `get_share_price(symbol)`
- `Account`

## Core capabilities
- cash management
- stock trading simulation
- portfolio valuation
- profit/loss calculation
- transaction history
- holdings reporting
- validation and error handling

This design is intentionally self-contained so the engineer can implement it in a single `accounts.py` file and immediately test it or attach a UI layer on top.