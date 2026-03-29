# Requirements Specification — Trading Simulation Account Management System

## 1. Purpose

This document defines the refined requirements for a simple account management system used in a trading simulation platform. The system allows a user to manage cash, buy/sell shares, view portfolio value, track profit/loss, and inspect transaction history.

This specification resolves ambiguities in the raw requirements and provides a clear basis for implementation and testing.

---

## 2. Scope

The system shall support:

- Creating a user account
- Depositing and withdrawing cash
- Buying and selling shares by symbol and quantity
- Calculating current portfolio value
- Calculating profit/loss relative to the user’s initial deposited cash
- Reporting current holdings at any point in time
- Reporting transaction history
- Preventing invalid operations such as overspending, overdrawing, and selling unavailable shares

The system uses an external/share-price lookup function:

- `get_share_price(symbol)` → returns the current price for a given share symbol

A test implementation is provided with fixed prices for:

- `AAPL`
- `TSLA`
- `GOOGL`

---

## 3. Definitions

### 3.1 Account
A single trading simulation user record containing:
- Cash balance
- Share holdings
- Transaction history
- Initial deposited amount

### 3.2 Holdings
The number of shares currently owned per symbol.

### 3.3 Portfolio Value
The total value of the account at a point in time:

- Cash balance
- Plus market value of all held shares at current prices

### 3.4 Profit/Loss (P/L)
The difference between current portfolio value and the user’s initial deposited cash.

> **Resolved ambiguity:** Profit/loss is measured against the initial deposit amount, not against cumulative deposits unless otherwise specified.

### 3.5 Transaction
A recorded account event such as:
- Account creation
- Deposit
- Withdrawal
- Buy
- Sell

---

## 4. Assumptions and Clarifications

To remove ambiguity, the following rules apply:

1. **Single account per user context**
   - The system manages one simulated account per user session or profile.
   - If multiple accounts are needed later, that is out of scope for this requirement set.

2. **Cash-based trading**
   - Buys and sells are executed using current prices from `get_share_price(symbol)`.

3. **Buy/sell execution price**
   - The transaction uses the share price returned at the time of the operation.
   - The executed price must be stored in transaction history.

4. **No short selling**
   - Users may not sell more shares of a symbol than they currently hold.

5. **No margin**
   - Users may not buy shares unless they have sufficient available cash.
   - Users may not withdraw cash that would result in a negative cash balance.

6. **Initial deposit basis for P/L**
   - Profit or loss is computed using the first deposit amount as the basis.
   - If no deposit has been made, P/L is zero or undefined until the first deposit; for implementation purposes, it should be reported as zero until initial deposit exists.

7. **Supported symbols**
   - The system depends on `get_share_price(symbol)` for market pricing.
   - If the function cannot provide a price for a symbol, the buy/sell operation must fail.

8. **Quantity handling**
   - Share quantities must be positive whole numbers.
   - Fractional shares are not supported unless explicitly added later.

9. **Transactions are immutable**
   - Once recorded, transaction entries must not be altered.

10. **Time concept**
    - “At any point in time” means the system can report the current state based on all recorded transactions up to now.
    - Historical snapshots are not required unless explicitly stored.

---

## 5. Functional Requirements

### FR-1: Create Account
The system shall allow a user to create an account.

#### Acceptance criteria:
- An account can be created with an empty cash balance and no holdings.
- Transaction history starts empty or includes an `ACCOUNT_CREATED` event if design chooses to record it.
- The account must be in a valid state after creation.

---

### FR-2: Deposit Funds
The system shall allow a user to deposit funds into the account.

#### Rules:
- Deposit amount must be greater than zero.
- Deposits increase cash balance by the deposited amount.
- Deposits are recorded in transaction history.
- The first deposit establishes the initial deposit amount used for profit/loss calculations.

#### Acceptance criteria:
- A valid deposit increases available cash.
- A deposit of zero or negative value is rejected.

---

### FR-3: Withdraw Funds
The system shall allow a user to withdraw funds from the account.

#### Rules:
- Withdrawal amount must be greater than zero.
- Withdrawal must not reduce cash balance below zero.
- Withdrawal is recorded in transaction history.

#### Acceptance criteria:
- Withdrawal succeeds only if sufficient cash is available.
- A withdrawal that would cause a negative cash balance is rejected.
- A zero or negative withdrawal is rejected.

---

### FR-4: Buy Shares
The system shall allow a user to buy shares by providing a share symbol and quantity.

#### Rules:
- Quantity must be a positive whole number.
- The system shall call `get_share_price(symbol)` to determine the current buy price.
- Total buy cost = current price × quantity.
- The user must have sufficient cash to cover the total buy cost.
- On success:
  - Cash balance decreases by total buy cost
  - Holdings for the symbol increase by quantity
  - Transaction is recorded

#### Acceptance criteria:
- Buying updates holdings and cash correctly.
- Buying more shares than affordable is rejected.
- Buying a symbol with unavailable price data is rejected.
- Buying zero, negative, or non-integer quantity is rejected.

---

### FR-5: Sell Shares
The system shall allow a user to sell shares by providing a share symbol and quantity.

#### Rules:
- Quantity must be a positive whole number.
- The system shall call `get_share_price(symbol)` to determine the current sell price.
- Total sell proceeds = current price × quantity.
- The user must own at least the quantity being sold.
- On success:
  - Cash balance increases by total sell proceeds
  - Holdings for the symbol decrease by quantity
  - Transaction is recorded
  - If a holding reaches zero, it may remain in the holdings list with quantity zero or be removed; implementation must be consistent

#### Acceptance criteria:
- Selling updates holdings and cash correctly.
- Selling more shares than owned is rejected.
- Selling a symbol with unavailable price data is rejected.
- Selling zero, negative, or non-integer quantity is rejected.

---

### FR-6: Calculate Portfolio Value
The system shall calculate the total current value of the portfolio.

#### Formula:
Portfolio value = cash balance + sum of (quantity held × current share price) for all held symbols

#### Acceptance criteria:
- Cash is included in portfolio value.
- Only current holdings are included.
- Current prices are obtained through `get_share_price(symbol)`.

---

### FR-7: Calculate Profit/Loss
The system shall calculate profit or loss relative to the initial deposit.

#### Formula:
Profit/Loss = current portfolio value − initial deposit amount

#### Acceptance criteria:
- If current portfolio value exceeds initial deposit, P/L is positive.
- If current portfolio value is below initial deposit, P/L is negative.
- The initial deposit amount is fixed as the first successful deposit amount.

---

### FR-8: Report Holdings
The system shall report the user’s current holdings at any point in time.

#### Output:
For each symbol:
- Symbol
- Quantity owned
- Optional current market value per symbol

#### Acceptance criteria:
- The report reflects the current account state.
- Symbols with zero holdings may be omitted or included depending on implementation, but the behavior must be consistent and documented.

---

### FR-9: Report Profit/Loss
The system shall report the user’s current profit or loss at any point in time.

#### Acceptance criteria:
- The report must use the same calculation as FR-7.
- The value must reflect the current market prices.

---

### FR-10: List Transactions
The system shall list all transactions the user has made over time.

#### Transaction history shall include:
- Transaction type
- Timestamp or sequence order
- Amounts/quantities
- Share symbol if applicable
- Executed price for buy/sell transactions
- Resulting balance and/or holdings after the transaction, if supported

#### Acceptance criteria:
- Transactions are returned in chronological order.
- The list includes all successful transactions.
- Failed transactions are not included in the account history unless explicitly required for audit logging.

---

### FR-11: Validate and Reject Invalid Operations
The system shall reject operations that violate account rules.

#### Invalid conditions include:
- Withdraw causing negative cash balance
- Buy exceeding available cash
- Sell exceeding owned quantity
- Negative or zero deposit/withdrawal/buy/sell amount
- Invalid share symbol if price is unavailable
- Non-integer share quantity

#### Acceptance criteria:
- Invalid actions fail atomically.
- State does not change when validation fails.
- A meaningful error message or error code is returned.

---

## 6. Data Requirements

### 6.1 Account Data
The system shall store, at minimum:

- Account ID or account identifier
- Cash balance
- Initial deposit amount
- Holdings by symbol
- Transaction history

### 6.2 Transaction Record Fields
Each transaction record should contain:

- Transaction ID
- Timestamp or sequential order
- Transaction type
- Symbol, if applicable
- Quantity, if applicable
- Unit price, if applicable
- Total amount
- Post-transaction cash balance
- Post-transaction holding quantity, if applicable
- Status if transaction processing can fail

---

## 7. Non-Functional Requirements

### NFR-1: Correctness
All balance, holding, and valuation calculations must be accurate and deterministic for the same inputs.

### NFR-2: Traceability
All successful financial and trading actions must be recorded in transaction history.

### NFR-3: Consistency
Account state changes must be atomic:
- Either the full operation succeeds
- Or no state changes occur

### NFR-4: Usability
Error responses must clearly indicate why an operation failed.

### NFR-5: Performance
The system should be able to compute holdings, portfolio value, and transaction history without excessive delay for normal simulated account sizes.

### NFR-6: Testability
The system must support the provided test price function and predictable fixed-price behavior for:
- `AAPL`
- `TSLA`
- `GOOGL`

### NFR-7: Maintainability
Pricing access must be abstracted through `get_share_price(symbol)` so that pricing sources can be replaced without changing core account logic.

---

## 8. Constraints

### C-1: Dependence on Share Price Function
The system must use `get_share_price(symbol)` as the source of current market price.

### C-2: Supported Asset Types
Only shares/stocks are in scope. No options, bonds, crypto, or leveraged instruments.

### C-3: No Negative Cash Balance
Cash balance cannot drop below zero at any time.

### C-4: No Short Selling
Users cannot sell shares they do not own.

### C-5: No Margin Trading
Users cannot purchase shares without sufficient available cash.

### C-6: Quantity Must Be Integer
Share quantities must be whole numbers.

### C-7: Initial Deposit Basis
Profit/loss calculations must reference the first deposit amount as the baseline.

### C-8: Simulation Context
This is a trading simulation; no real money movement, settlement delay, taxes, fees, or commissions are included unless added later.

---

## 9. Edge Cases

The implementation must explicitly handle the following edge cases:

### EC-1: Account Created but No Deposit Yet
- Cash balance is zero.
- Portfolio value may be zero unless holdings exist through some other allowed path.
- Profit/loss should be zero or clearly defined as zero until first deposit.

### EC-2: Zero or Negative Amounts
- Deposits, withdrawals, buys, and sells with zero or negative values must be rejected.

### EC-3: Fractional Quantities
- If a non-integer quantity is provided, the operation must be rejected.

### EC-4: Unknown Symbol
- If `get_share_price(symbol)` cannot provide a price, buy/sell must fail.
- The system must not create holdings for unsupported symbols.

### EC-5: Exact Balance Depletion
- Buying or withdrawing that reduces cash to exactly zero is allowed, provided it does not go below zero.

### EC-6: Exact Quantity Depletion
- Selling the full quantity of a held symbol is allowed.
- The resulting holding for that symbol becomes zero and must be handled consistently.

### EC-7: Multiple Deposits
- Only the first successful deposit defines the initial deposit basis for profit/loss.
- Subsequent deposits increase cash but do not change initial deposit basis.

### EC-8: Empty Transaction History
- The system should return an empty list or equivalent when no transactions have occurred.

### EC-9: Price Changes Over Time
- Portfolio value and P/L use current prices at the time of query, not historical purchase prices.

### EC-10: Concurrent State Changes
- If concurrency is supported in the future, read-modify-write operations must remain consistent.
- For this requirement set, concurrency handling is not mandated unless the system is multi-user shared state.

---

## 10. Suggested Error Handling Rules

The following error conditions should be surfaced clearly:

- `INSUFFICIENT_FUNDS` — withdrawal or buy would exceed available cash
- `INSUFFICIENT_SHARES` — sell exceeds holdings
- `INVALID_AMOUNT` — amount or quantity is zero or negative
- `INVALID_QUANTITY` — quantity is not a whole number
- `UNKNOWN_SYMBOL` — no price available for the requested symbol
- `ACCOUNT_NOT_INITIALIZED` — operation attempted before account creation, if applicable

---

## 11. Acceptance Scenarios

### Scenario 1: Create account and deposit cash
1. User creates an account
2. User deposits 1000
3. Cash balance becomes 1000
4. Initial deposit basis becomes 1000

### Scenario 2: Buy shares successfully
1. User has 1000 cash
2. `get_share_price(AAPL)` returns 100
3. User buys 5 AAPL
4. Cash balance decreases by 500
5. Holdings show 5 AAPL

### Scenario 3: Reject unaffordable buy
1. User has 100 cash
2. `get_share_price(TSLA)` returns 200
3. User attempts to buy 1 TSLA
4. Operation is rejected
5. State remains unchanged

### Scenario 4: Sell shares successfully
1. User holds 3 GOOGL
2. `get_share_price(GOOGL)` returns 150
3. User sells 2 GOOGL
4. Cash increases by 300
5. Holdings show 1 GOOGL

### Scenario 5: Reject oversell
1. User holds 2 AAPL
2. User attempts to sell 3 AAPL
3. Operation is rejected
4. State remains unchanged

### Scenario 6: Report portfolio value and P/L
1. User deposited 1000
2. User holds shares with current market value 200
3. Cash balance is 800
4. Portfolio value = 1000
5. Profit/Loss = 0

---

## 12. Out of Scope

The following are not included in the current requirements:

- Multiple user accounts with authentication and roles
- Order books, limit orders, market orders, or partial fills
- Trading fees, commissions, taxes, dividends, or corporate actions
- Historical price snapshots
- Short selling or margin trading
- Real-time market streaming
- Persistent storage requirements
- Multi-currency support
- Fractional shares

---

## 13. Implementation Notes for Engineering

1. Use a single source of truth for cash balance and holdings.
2. Always validate before mutating account state.
3. Record executed trade price in transaction history for buy/sell events.
4. Use current price lookups only when calculating portfolio value and validating/executing trades.
5. Ensure buy/sell operations are atomic.
6. Keep calculations deterministic and testable using the fixed-price test implementation.

---

## 14. Summary of Core Business Rules

- Users can deposit and withdraw cash.
- Users can buy and sell shares by symbol and quantity.
- Users cannot overdraw cash, overspend, or oversell.
- Portfolio value is current cash plus current market value of holdings.
- Profit/loss is portfolio value minus the first deposit.
- Holdings and transaction history must be reportable at any time.
- Share prices are retrieved through `get_share_price(symbol)`.