import unittest
from datetime import datetime, timezone

from accounts import (
    Account,
    AccountError,
    InsufficientFundsError,
    InsufficientHoldingsError,
    Transaction,
    Position,
    UnknownSymbolError,
    get_share_price,
)


class TestGetSharePrice(unittest.TestCase):
    def test_known_symbols_are_case_insensitive_and_strip_whitespace(self):
        self.assertEqual(get_share_price("AAPL"), 190.0)
        self.assertEqual(get_share_price("aapl"), 190.0)
        self.assertEqual(get_share_price("  TsLa "), 250.0)

    def test_invalid_symbol_raises_unknown_symbol_error(self):
        with self.assertRaises(UnknownSymbolError):
            get_share_price("")
        with self.assertRaises(UnknownSymbolError):
            get_share_price(" ")
        with self.assertRaises(UnknownSymbolError):
            get_share_price(None)  # type: ignore[arg-type]

    def test_unknown_symbol_raises_unknown_symbol_error(self):
        with self.assertRaises(UnknownSymbolError) as ctx:
            get_share_price("MSFT")
        self.assertIn("Unknown symbol", str(ctx.exception))


class TestDataclasses(unittest.TestCase):
    def test_transaction_to_dict_returns_expected_structure(self):
        ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        txn = Transaction(
            timestamp=ts,
            transaction_type="deposit",
            amount=100.0,
            cash_balance_after=100.0,
            holdings_after={"AAPL": 2},
        )
        expected = {
            "timestamp": ts.isoformat(),
            "transaction_type": "deposit",
            "amount": 100.0,
            "symbol": None,
            "quantity": None,
            "price": None,
            "cash_balance_after": 100.0,
            "holdings_after": {"AAPL": 2},
        }
        self.assertEqual(txn.to_dict(), expected)

    def test_position_to_dict_returns_expected_structure(self):
        pos = Position(
            symbol="AAPL",
            quantity=3,
            current_price=190.0,
            market_value=570.0,
        )
        self.assertEqual(
            pos.to_dict(),
            {
                "symbol": "AAPL",
                "quantity": 3,
                "current_price": 190.0,
                "market_value": 570.0,
            },
        )


class TestAccountInitialization(unittest.TestCase):
    def test_invalid_account_id_raises_value_error(self):
        with self.assertRaises(ValueError):
            Account("")
        with self.assertRaises(ValueError):
            Account("   ")
        with self.assertRaises(ValueError):
            Account(None)  # type: ignore[arg-type]

    def test_account_initial_state(self):
        account = Account("acct-1", "Alice")
        self.assertEqual(account.account_id, "acct-1")
        self.assertEqual(account.owner_name, "Alice")
        self.assertEqual(account.cash_balance, 0.0)
        self.assertEqual(account.initial_deposit, 0.0)
        self.assertEqual(account.holdings, {})
        self.assertEqual(account.transactions, [])
        self.assertEqual(account._total_deposits, 0.0)
        self.assertEqual(account._total_withdrawals, 0.0)


class TestAccountValidationHelpers(unittest.TestCase):
    def setUp(self):
        self.account = Account("acct-1")

    def test_validate_amount(self):
        for bad in [0, -1, 0.0, -0.5, True, "10", None]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self.account._validate_amount(bad)  # type: ignore[arg-type]

    def test_validate_quantity(self):
        for bad in [0, -1, 1.2, True, "2", None]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self.account._validate_quantity(bad)  # type: ignore[arg-type]

    def test_get_holding_quantity_is_case_insensitive(self):
        self.account.holdings["AAPL"] = 5
        self.assertEqual(self.account._get_holding_quantity("aapl"), 5)
        self.assertEqual(self.account._get_holding_quantity("MSFT"), 0)


class TestAccountOperations(unittest.TestCase):
    def setUp(self):
        self.account = Account("acct-1", "Alice")

    def test_deposit_updates_balance_initial_deposit_and_transaction(self):
        self.account.deposit(100)
        self.assertEqual(self.account.cash_balance, 100.0)
        self.assertEqual(self.account.initial_deposit, 100.0)
        self.assertEqual(self.account._total_deposits, 100.0)
        self.assertEqual(len(self.account.transactions), 1)
        txn = self.account.transactions[0]
        self.assertEqual(txn.transaction_type, "deposit")
        self.assertEqual(txn.amount, 100.0)
        self.assertEqual(txn.cash_balance_after, 100.0)
        self.assertEqual(txn.holdings_after, {})

    def test_second_deposit_does_not_change_initial_deposit(self):
        self.account.deposit(100)
        self.account.deposit(50)
        self.assertEqual(self.account.initial_deposit, 100.0)
        self.assertEqual(self.account.cash_balance, 150.0)
        self.assertEqual(self.account._total_deposits, 150.0)
        self.assertEqual(len(self.account.transactions), 2)

    def test_withdraw_updates_balance_and_transaction(self):
        self.account.deposit(100)
        self.account.withdraw(40)
        self.assertEqual(self.account.cash_balance, 60.0)
        self.assertEqual(self.account._total_withdrawals, 40.0)
        self.assertEqual(len(self.account.transactions), 2)
        txn = self.account.transactions[-1]
        self.assertEqual(txn.transaction_type, "withdrawal")
        self.assertEqual(txn.amount, 40.0)
        self.assertEqual(txn.cash_balance_after, 60.0)

    def test_withdraw_more_than_balance_raises_insufficient_funds(self):
        self.account.deposit(50)
        with self.assertRaises(InsufficientFundsError):
            self.account.withdraw(60)
        self.assertEqual(self.account.cash_balance, 50.0)
        self.assertEqual(len(self.account.transactions), 1)

    def test_buy_shares_updates_holdings_balance_and_transaction(self):
        self.account.deposit(1000)
        self.account.buy_shares("aapl", 2)
        self.assertEqual(self.account.cash_balance, 620.0)
        self.assertEqual(self.account.holdings, {"AAPL": 2})
        self.assertEqual(len(self.account.transactions), 2)
        txn = self.account.transactions[-1]
        self.assertEqual(txn.transaction_type, "buy")
        self.assertEqual(txn.symbol, "AAPL")
        self.assertEqual(txn.quantity, 2)
        self.assertEqual(txn.price, 190.0)
        self.assertEqual(txn.amount, 380.0)
        self.assertEqual(txn.cash_balance_after, 620.0)
        self.assertEqual(txn.holdings_after, {"AAPL": 2})

    def test_buy_shares_with_insufficient_cash_raises_error(self):
        self.account.deposit(100)
        with self.assertRaises(InsufficientFundsError):
            self.account.buy_shares("AAPL", 1)
        self.assertEqual(self.account.cash_balance, 100.0)
        self.assertEqual(self.account.holdings, {})
        self.assertEqual(len(self.account.transactions), 1)

    def test_buy_shares_unknown_symbol_raises_error(self):
        self.account.deposit(1000)
        with self.assertRaises(UnknownSymbolError):
            self.account.buy_shares("MSFT", 1)
        self.assertEqual(self.account.cash_balance, 1000.0)
        self.assertEqual(self.account.holdings, {})
        self.assertEqual(len(self.account.transactions), 1)

    def test_sell_shares_updates_balance_and_removes_holding_when_zero(self):
        self.account.deposit(1000)
        self.account.buy_shares("AAPL", 2)
        self.account.sell_shares("aapl", 2)
        self.assertEqual(self.account.cash_balance, 1000.0)
        self.assertEqual(self.account.holdings, {})
        self.assertEqual(len(self.account.transactions), 3)
        txn = self.account.transactions[-1]
        self.assertEqual(txn.transaction_type, "sell")
        self.assertEqual(txn.symbol, "AAPL")
        self.assertEqual(txn.quantity, 2)
        self.assertEqual(txn.price, 190.0)
        self.assertEqual(txn.amount, 380.0)

    def test_sell_shares_partially_reduces_holding(self):
        self.account.deposit(1000)
        self.account.buy_shares("AAPL", 3)
        self.account.sell_shares("AAPL", 1)
        self.assertEqual(self.account.cash_balance, 810.0)
        self.assertEqual(self.account.holdings, {"AAPL": 2})

    def test_sell_shares_more_than_owned_raises_error(self):
        self.account.deposit(1000)
        self.account.buy_shares("AAPL", 1)
        with self.assertRaises(InsufficientHoldingsError):
            self.account.sell_shares("AAPL", 2)
        self.assertEqual(self.account.holdings, {"AAPL": 1})
        self.assertEqual(self.account.cash_balance, 810.0)

    def test_sell_shares_unknown_symbol_raises_error_when_owned_zero(self):
        self.account.deposit(1000)
        with self.assertRaises(InsufficientHoldingsError):
            self.account.sell_shares("MSFT", 1)

    def test_get_holdings_returns_copy(self):
        self.account.holdings["AAPL"] = 1
        holdings = self.account.get_holdings()
        holdings["AAPL"] = 99
        self.assertEqual(self.account.holdings["AAPL"], 1)

    def test_get_cash_balance_returns_float(self):
        self.account.deposit(10)
        self.assertIsInstance(self.account.get_cash_balance(), float)
        self.assertEqual(self.account.get_cash_balance(), 10.0)

    def test_get_portfolio_value_with_holdings(self):
        self.account.deposit(1000)
        self.account.buy_shares("AAPL", 2)
        self.account.buy_shares("TSLA", 1)
        expected = 620.0 + 380.0 + 250.0
        self.assertEqual(self.account.get_portfolio_value(), expected)

    def test_get_profit_loss_after_transactions(self):
        self.account.deposit(1000)
        self.account.buy_shares("AAPL", 2)
        self.account.sell_shares("AAPL", 1)
        # Portfolio value = cash 810 + 1 AAPL 190 = 1000
        # Net deposits - withdrawals = 1000
        self.assertEqual(self.account.get_profit_loss(), 0.0)

    def test_get_transaction_history_returns_copy(self):
        self.account.deposit(100)
        history = self.account.get_transaction_history()
        self.assertEqual(len(history), 1)
        history.append("mutated")
        self.assertEqual(len(self.account.transactions), 1)

    def test_get_positions_returns_position_objects(self):
        self.account.deposit(1000)
        self.account.buy_shares("AAPL", 2)
        positions = self.account.get_positions()
        self.assertEqual(len(positions), 1)
        pos = positions[0]
        self.assertIsInstance(pos, Position)
        self.assertEqual(pos.symbol, "AAPL")
        self.assertEqual(pos.quantity, 2)
        self.assertEqual(pos.current_price, 190.0)
        self.assertEqual(pos.market_value, 380.0)

    def test_to_dict_contains_expected_keys_and_values(self):
        self.account.deposit(1000)
        self.account.buy_shares("AAPL", 2)
        data = self.account.to_dict()
        self.assertEqual(data["account_id"], "acct-1")
        self.assertEqual(data["owner_name"], "Alice")
        self.assertEqual(data["cash_balance"], 620.0)
        self.assertEqual(data["holdings"], {"AAPL": 2})
        self.assertEqual(data["portfolio_value"], 1000.0)
        self.assertEqual(data["profit_loss"], 0.0)
        self.assertEqual(data["initial_deposit"], 1000.0)
        self.assertEqual(len(data["transactions"]), 2)
        self.assertEqual(len(data["positions"]), 1)
        self.assertEqual(data["positions"][0]["symbol"], "AAPL")

    def test_transactions_are_immutable_dataclass_instances(self):
        self.account.deposit(100)
        txn = self.account.transactions[0]
        with self.assertRaises(Exception):
            txn.amount = 200  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()