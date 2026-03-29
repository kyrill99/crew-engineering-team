import unittest
import importlib
from decimal import Decimal
from datetime import datetime
from dataclasses import FrozenInstanceError
import sys


def _import_module(*names):
    last_exc = None
    for name in names:
        try:
            return importlib.import_module(name)
        except Exception as exc:
            last_exc = exc
    raise last_exc


errors_mod = _import_module("errors")
models_mod = _import_module("models")
price_provider_mod = _import_module("price_provider")
fixed_price_provider_mod = _import_module("fixed_price_provider")
validation_mod = _import_module("validation")
account_state_mod = _import_module("account_state")
portfolio_service_mod = _import_module("portfolio_service")
account_service_mod = _import_module("account_service")
factory_mod = _import_module("factory")

AccountError = errors_mod.AccountError
TransactionType = models_mod.TransactionType
Transaction = models_mod.Transaction
PriceProvider = price_provider_mod.PriceProvider
PriceProviderError = price_provider_mod.PriceProviderError
FixedPriceProvider = fixed_price_provider_mod.FixedPriceProvider
default_price_source = price_provider_mod.default_price_source
AccountValidator = validation_mod.AccountValidator
AccountState = account_state_mod.AccountState
PortfolioService = portfolio_service_mod.PortfolioService
AccountService = account_service_mod.AccountService
AccountServiceFactory = factory_mod.AccountServiceFactory


class TestAccountError(unittest.TestCase):
    def test_str_and_attributes(self):
        err = AccountError("bad thing", "BAD_CODE")
        self.assertEqual(err.message, "bad thing")
        self.assertEqual(err.code, "BAD_CODE")
        self.assertEqual(str(err), "BAD_CODE: bad thing")
        self.assertEqual(err.args[0], "bad thing")


class TestTransactionModel(unittest.TestCase):
    def setUp(self):
        self.base = Transaction(
            transaction_type=TransactionType.ACCOUNT_CREATED,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            account_id="acct-1",
        )

    def test_properties(self):
        self.assertTrue(self.base.is_account_created)
        self.assertFalse(self.base.is_cash_transaction)
        self.assertFalse(self.base.is_trade)

        deposit = self.base.create_deposit(Decimal("10.00"), Decimal("10.00"), datetime(2024, 1, 1, 12, 1, 0))
        self.assertTrue(deposit.is_cash_transaction)
        self.assertFalse(deposit.is_trade)

        buy = self.base.create_buy(
            "aapl", 2, Decimal("190.00"), Decimal("380.00"), Decimal("620.00"), 2, datetime(2024, 1, 1, 12, 2, 0)
        )
        self.assertTrue(buy.is_trade)

    def test_create_account_created(self):
        tx = self.base.create_account_created("  acct-2  ", datetime(2024, 1, 1, 13, 0, 0))
        self.assertEqual(tx.transaction_type, TransactionType.ACCOUNT_CREATED)
        self.assertEqual(tx.account_id, "acct-2")

    def test_create_deposit_and_withdrawal(self):
        dep = self.base.create_deposit(Decimal("100.25"), Decimal("100.25"), datetime(2024, 1, 1, 13, 0, 0))
        self.assertEqual(dep.amount, Decimal("100.25"))
        self.assertEqual(dep.post_cash_balance, Decimal("100.25"))
        self.assertEqual(dep.account_id, "acct-1")

        wd = self.base.create_withdrawal(Decimal("40.25"), Decimal("60.00"), datetime(2024, 1, 1, 13, 1, 0))
        self.assertEqual(wd.amount, Decimal("40.25"))
        self.assertEqual(wd.post_cash_balance, Decimal("60.00"))

    def test_create_buy_and_sell(self):
        buy = self.base.create_buy(
            "tsla", 3, Decimal("250.00"), Decimal("750.00"), Decimal("250.00"), 3, datetime(2024, 1, 1, 13, 0, 0)
        )
        self.assertEqual(buy.symbol, "TSLA")
        self.assertEqual(buy.quantity, 3)
        self.assertEqual(buy.unit_price, Decimal("250.00"))
        self.assertEqual(buy.total_amount, Decimal("750.00"))
        self.assertEqual(buy.post_holding_quantity, 3)

        sell = self.base.create_sell(
            "googl", 1, Decimal("140.00"), Decimal("140.00"), Decimal("390.00"), 0, datetime(2024, 1, 1, 13, 1, 0)
        )
        self.assertEqual(sell.symbol, "GOOGL")
        self.assertEqual(sell.transaction_type, TransactionType.SELL)

    def test_transaction_is_immutable(self):
        tx = self.base.create_deposit(Decimal("1.00"), Decimal("1.00"), datetime(2024, 1, 1, 13, 0, 0))
        with self.assertRaises(FrozenInstanceError):
            tx.account_id = "other"

    def test_validation_errors(self):
        with self.assertRaises(AccountError):
            self.base.create_account_created("", datetime(2024, 1, 1, 1, 1, 1))
        with self.assertRaises(AccountError):
            self.base.create_account_created("x", "not datetime")
        with self.assertRaises(AccountError):
            self.base.create_deposit(-Decimal("1.00"), Decimal("0.00"), datetime.utcnow())
        with self.assertRaises(AccountError):
            self.base.create_withdrawal("bad", Decimal("0.00"), datetime.utcnow())
        with self.assertRaises(AccountError):
            self.base.create_buy("AAPL", 0, Decimal("1"), Decimal("0"), Decimal("0"), 0, datetime.utcnow())
        with self.assertRaises(AccountError):
            self.base.create_buy("AAPL", 1, Decimal("1"), Decimal("2"), Decimal("0"), 0, datetime.utcnow())
        with self.assertRaises(AccountError):
            self.base.create_sell("AAPL", 1, Decimal("1"), Decimal("2"), Decimal("0"), -1, datetime.utcnow())


class TestPriceProvider(unittest.TestCase):
    def test_callable_requirement(self):
        with self.assertRaises(PriceProviderError):
            PriceProvider(price_source=None)

    def test_get_share_price_normalizes_and_quantizes(self):
        provider = PriceProvider(price_source=lambda symbol: "190.005")
        self.assertEqual(provider.get_share_price(" aapl "), Decimal("190.01"))

    def test_price_lookup_failure(self):
        provider = PriceProvider(price_source=lambda symbol: (_ for _ in ()).throw(RuntimeError("boom")))
        with self.assertRaises(PriceProviderError) as cm:
            provider.get_share_price("AAPL")
        self.assertEqual(cm.exception.code, "PRICE_LOOKUP_FAILED")

    def test_invalid_symbol_and_price(self):
        provider = PriceProvider(price_source=lambda symbol: "10")
        with self.assertRaises(PriceProviderError):
            provider.get_share_price("   ")

        provider2 = PriceProvider(price_source=lambda symbol: Decimal("0"))
        with self.assertRaises(PriceProviderError) as cm:
            provider2.get_share_price("AAPL")
        self.assertEqual(cm.exception.code, "INVALID_PRICE")

        provider3 = PriceProvider(price_source=lambda symbol: "not-a-number")
        with self.assertRaises(PriceProviderError):
            provider3.get_share_price("AAPL")

    def test_fixed_price_provider_defaults(self):
        provider = FixedPriceProvider()
        self.assertEqual(provider.get_share_price("AAPL"), Decimal("190.00"))
        self.assertEqual(provider.get_share_price("tsla"), Decimal("250.00"))
        self.assertEqual(provider.get_share_price(" GOOGL "), Decimal("140.00"))

    def test_fixed_price_provider_custom_prices_and_unknown_symbol(self):
        provider = FixedPriceProvider({"AAPL": "101.1", "MSFT": 330})
        self.assertEqual(provider.get_share_price("AAPL"), Decimal("101.10"))
        self.assertEqual(provider.get_share_price("msft"), Decimal("330.00"))
        with self.assertRaises(PriceProviderError) as cm:
            provider.get_share_price("TSLA")
        self.assertEqual(cm.exception.code, "UNKNOWN_SYMBOL")

    def test_default_price_source(self):
        self.assertEqual(default_price_source("AAPL"), Decimal("190.00"))


class TestAccountValidator(unittest.TestCase):
    def setUp(self):
        self.validator = AccountValidator()

    def test_validate_positive_amount(self):
        self.validator.validate_positive_amount(Decimal("1.00"))
        with self.assertRaises(AccountError):
            self.validator.validate_positive_amount(Decimal("0"))
        with self.assertRaises(AccountError):
            self.validator.validate_positive_amount(Decimal("-1"))
        with self.assertRaises(AccountError):
            self.validator.validate_positive_amount(1)

    def test_validate_positive_integer_quantity(self):
        self.validator.validate_positive_integer_quantity(1)
        with self.assertRaises(AccountError):
            self.validator.validate_positive_integer_quantity(0)
        with self.assertRaises(AccountError):
            self.validator.validate_positive_integer_quantity(True)
        with self.assertRaises(AccountError):
            self.validator.validate_positive_integer_quantity(1.5)

    def test_validate_symbol_price_available(self):
        price = self.validator.validate_symbol_price_available(" aapl ", lambda s: Decimal("190.00"))
        self.assertEqual(price, Decimal("190.00"))
        with self.assertRaises(AccountError) as cm:
            self.validator.validate_symbol_price_available("", lambda s: Decimal("1"))
        self.assertEqual(cm.exception.code, "SYMBOL_PRICE_UNAVAILABLE")
        with self.assertRaises(AccountError):
            self.validator.validate_symbol_price_available("AAPL", lambda s: Decimal("0"))
        with self.assertRaises(AccountError):
            self.validator.validate_symbol_price_available("AAPL", lambda s: "bad")

    def test_validate_sufficient_cash(self):
        self.validator.validate_sufficient_cash(Decimal("10"), Decimal("9"))
        with self.assertRaises(AccountError):
            self.validator.validate_sufficient_cash(Decimal("9"), Decimal("10"))
        with self.assertRaises(AccountError):
            self.validator.validate_sufficient_cash(Decimal("-1"), Decimal("1"))
        with self.assertRaises(AccountError):
            self.validator.validate_sufficient_cash(Decimal("1"), Decimal("-1"))

    def test_validate_sufficient_shares(self):
        self.validator.validate_sufficient_shares(10, 5)
        with self.assertRaises(AccountError):
            self.validator.validate_sufficient_shares(4, 5)
        with self.assertRaises(AccountError):
            self.validator.validate_sufficient_shares(-1, 1)
        with self.assertRaises(AccountError):
            self.validator.validate_sufficient_shares(1, -1)
        with self.assertRaises(AccountError):
            self.validator.validate_sufficient_shares(True, 1)


class TestAccountState(unittest.TestCase):
    def setUp(self):
        self.state = AccountState(" acct-1 ")

    def test_initial_state(self):
        self.assertEqual(self.state.account_id, "acct-1")
        self.assertEqual(self.state.cash_balance, Decimal("0"))
        self.assertEqual(self.state.initial_deposit_basis, Decimal("0"))
        self.assertEqual(self.state.holdings, {})
        self.assertEqual(len(self.state.transactions), 1)
        self.assertEqual(self.state.transactions[0].transaction_type, TransactionType.ACCOUNT_CREATED)

    def test_deposit_withdrawal(self):
        tx1 = self.state.apply_deposit(Decimal("100.00"), datetime(2024, 1, 1, 10, 0, 0))
        self.assertEqual(self.state.cash_balance, Decimal("100.00"))
        self.assertEqual(self.state.initial_deposit_basis, Decimal("100.00"))
        self.assertEqual(tx1.post_cash_balance, Decimal("100.00"))

        tx2 = self.state.apply_withdrawal(Decimal("30.00"), datetime(2024, 1, 1, 11, 0, 0))
        self.assertEqual(self.state.cash_balance, Decimal("70.00"))
        self.assertEqual(tx2.post_cash_balance, Decimal("70.00"))

    def test_buy_sell_and_holdings(self):
        self.state.apply_deposit(Decimal("1000.00"), datetime(2024, 1, 1, 10, 0, 0))
        buy = self.state.apply_buy("aapl", 2, Decimal("190.00"), datetime(2024, 1, 1, 10, 5, 0))
        self.assertEqual(self.state.cash_balance, Decimal("620.00"))
        self.assertEqual(self.state.get_holding_quantity("AAPL"), 2)
        self.assertEqual(self.state.get_holdings(), {"AAPL": 2})
        self.assertEqual(buy.post_holding_quantity, 2)

        sell = self.state.apply_sell("AAPL", 1, Decimal("190.00"), datetime(2024, 1, 1, 10, 6, 0))
        self.assertEqual(self.state.cash_balance, Decimal("810.00"))
        self.assertEqual(self.state.get_holding_quantity("AAPL"), 1)
        self.assertEqual(sell.post_holding_quantity, 1)

        sell2 = self.state.apply_sell("AAPL", 1, Decimal("190.00"), datetime(2024, 1, 1, 10, 7, 0))
        self.assertEqual(self.state.get_holdings(), {})
        self.assertEqual(sell2.post_holding_quantity, 0)

    def test_insufficient_funds_and_holdings(self):
        self.state.apply_deposit(Decimal("10.00"), datetime.utcnow())
        with self.assertRaises(AccountError) as cm:
            self.state.apply_withdrawal(Decimal("11.00"), datetime.utcnow())
        self.assertEqual(cm.exception.code, "INSUFFICIENT_FUNDS")

        with self.assertRaises(AccountError):
            self.state.apply_buy("AAPL", 1, Decimal("190.00"), datetime.utcnow())

        with self.assertRaises(AccountError):
            self.state.apply_sell("AAPL", 1, Decimal("1.00"), datetime.utcnow())

    def test_invalid_inputs(self):
        with self.assertRaises(AccountError):
            AccountState("")
        with self.assertRaises(AccountError):
            self.state.apply_deposit("bad", datetime.utcnow())
        with self.assertRaises(AccountError):
            self.state.apply_withdrawal(Decimal("1"), "bad")
        with self.assertRaises(AccountError):
            self.state.apply_buy("", 1, Decimal("1"), datetime.utcnow())
        with self.assertRaises(AccountError):
            self.state.apply_buy("AAPL", 0, Decimal("1"), datetime.utcnow())
        with self.assertRaises(AccountError):
            self.state.apply_sell("AAPL", 0, Decimal("1"), datetime.utcnow())

    def test_reporting_and_transactions_copy(self):
        self.state.apply_deposit(Decimal("100.00"), datetime.utcnow())
        txs = self.state.get_transactions()
        self.assertEqual(len(txs), 2)
        txs.append("x")
        self.assertEqual(len(self.state.get_transactions()), 2)
        self.assertEqual(self.state.get_holdings_snapshot(), {})
        self.assertEqual(self.state.list_transactions(), self.state.get_transactions())

    def test_portfolio_and_profit_loss(self):
        self.state.apply_deposit(Decimal("1000.00"), datetime.utcnow())
        self.state.apply_buy("AAPL", 2, Decimal("190.00"), datetime.utcnow())
        self.assertEqual(self.state.get_portfolio_value(), Decimal("1000.00"))
        self.assertEqual(self.state.get_profit_loss(), Decimal("0.00"))

        self.state.apply_sell("AAPL", 1, Decimal("190.00"), datetime.utcnow())
        self.assertEqual(self.state.get_portfolio_value(), Decimal("1000.00"))

        custom = self.state.get_portfolio_value(price_provider=lambda s: Decimal("200.00"))
        self.assertEqual(custom, Decimal("1010.00"))


class TestPortfolioService(unittest.TestCase):
    def setUp(self):
        self.state = AccountState("acct-1")
        self.state.apply_deposit(Decimal("1000.00"), datetime.utcnow())
        self.state.apply_buy("AAPL", 2, Decimal("190.00"), datetime.utcnow())
        self.state.apply_buy("TSLA", 1, Decimal("250.00"), datetime.utcnow())

    def test_requires_callable_provider(self):
        with self.assertRaises(AccountError):
            PortfolioService(price_provider=None)

    def test_holdings_value_portfolio_value_profit_loss(self):
        svc = PortfolioService(price_provider=FixedPriceProvider())
        self.assertEqual(svc.calculate_holdings_value(self.state), Decimal("630.00"))
        self.assertEqual(svc.calculate_portfolio_value(self.state), Decimal("1000.00"))
        self.assertEqual(svc.calculate_profit_loss(self.state), Decimal("0.00"))

    def test_build_holdings_report(self):
        svc = PortfolioService(price_provider=FixedPriceProvider())
        report = svc.build_holdings_report(self.state)
        self.assertEqual(len(report), 2)
        self.assertEqual(report[0]["symbol"], "AAPL")
        self.assertEqual(report[0]["quantity"], 2)
        self.assertEqual(report[0]["unit_price"], Decimal("190.00"))
        self.assertEqual(report[0]["market_value"], Decimal("380.00"))

    def test_ignores_non_positive_holdings_and_invalid_state(self):
        self.state.holdings["DUMMY"] = 0
        svc = PortfolioService(price_provider=lambda s: Decimal("1.00"))
        self.assertEqual(svc.calculate_holdings_value(self.state), Decimal("630.00"))
        with self.assertRaises(AccountError):
            svc.calculate_holdings_value("bad")

    def test_invalid_price(self):
        svc = PortfolioService(price_provider=lambda s: Decimal("0"))
        with self.assertRaises(AccountError):
            svc.calculate_holdings_value(self.state)


class TestAccountService(unittest.TestCase):
    def setUp(self):
        self.provider = FixedPriceProvider()
        self.service = AccountService(price_provider=self.provider.get_share_price)

    def test_requires_account(self):
        with self.assertRaises(AccountError):
            self.service.deposit(Decimal("1"))
        with self.assertRaises(AccountError):
            self.service.get_holdings()
        with self.assertRaises(AccountError):
            self.service.list_transactions()

    def test_create_account_once(self):
        self.service.create_account("acct-1")
        with self.assertRaises(AccountError):
            self.service.create_account("acct-2")

    def test_deposit_withdraw_buy_sell_reporting(self):
        self.service.create_account("acct-1")
        dep = self.service.deposit(Decimal("1000.00"))
        self.assertEqual(dep.amount, Decimal("1000.00"))

        buy = self.service.buy_shares("aapl", 2)
        self.assertEqual(buy.symbol, "AAPL")
        self.assertEqual(self.service.get_holdings(), {"AAPL": 2})

        self.assertEqual(self.service.get_portfolio_value(), Decimal("1000.00"))
        self.assertEqual(self.service.get_profit_loss(), Decimal("0.00"))

        sell = self.service.sell_shares("AAPL", 1)
        self.assertEqual(sell.quantity, 1)
        self.assertEqual(self.service.get_holdings(), {"AAPL": 1})

        wd = self.service.withdraw(Decimal("50.00"))
        self.assertEqual(wd.amount, Decimal("50.00"))
        self.assertEqual(self.service.get_portfolio_value(), Decimal("950.00"))

        txs = self.service.list_transactions()
        self.assertGreaterEqual(len(txs), 5)

    def test_prevents_negative_balance_and_overbuy_over_sell(self):
        self.service.create_account("acct-1")
        self.service.deposit(Decimal("100.00"))

        with self.assertRaises(AccountError) as cm:
            self.service.withdraw(Decimal("150.00"))
        self.assertEqual(cm.exception.code, "INSUFFICIENT_FUNDS")

        with self.assertRaises(AccountError):
            self.service.buy_shares("AAPL", 1)

        self.service.deposit(Decimal("1000.00"))
        self.service.buy_shares("AAPL", 2)
        with self.assertRaises(AccountError) as cm2:
            self.service.sell_shares("AAPL", 3)
        self.assertEqual(cm2.exception.code, "INSUFFICIENT_HOLDINGS")

    def test_invalid_inputs(self):
        self.service.create_account("acct-1")
        with self.assertRaises(AccountError):
            self.service.deposit("bad")
        with self.assertRaises(AccountError):
            self.service.withdraw("bad")
        with self.assertRaises(AccountError):
            self.service.buy_shares("", 1)
        with self.assertRaises(AccountError):
            self.service.buy_shares("AAPL", 0)
        with self.assertRaises(AccountError):
            self.service.sell_shares("AAPL", 0)

    def test_custom_price_provider_must_be_positive(self):
        bad_service = AccountService(price_provider=lambda s: Decimal("-1"))
        bad_service.create_account("acct-1")
        with self.assertRaises(AccountError):
            bad_service.buy_shares("AAPL", 1)


class TestAccountServiceFactory(unittest.TestCase):
    def test_create_with_fixed_prices(self):
        factory = AccountServiceFactory()
        service = factory.create_with_fixed_prices("acct-1")
        self.assertIsInstance(service, AccountService)
        self.assertEqual(service.get_holdings(), {})

    def test_create_with_price_provider(self):
        factory = AccountServiceFactory()
        provider = FixedPriceProvider()
        service = factory.create_with_price_provider("acct-1", provider)
        self.assertIsInstance(service, AccountService)

    def test_factory_invalid_provider(self):
        factory = AccountServiceFactory()
        with self.assertRaises(AccountError):
            factory.create_with_price_provider("acct-1", None)
        with self.assertRaises(AccountError):
            factory.create_with_price_provider("acct-1", object())

    def test_wired_service_works_end_to_end(self):
        factory = AccountServiceFactory()
        service = factory.create_with_fixed_prices("acct-1")
        service.deposit(Decimal("1000.00"))
        service.buy_shares("AAPL", 2)
        self.assertEqual(service.get_holdings(), {"AAPL": 2})
        self.assertEqual(service.get_portfolio_value(), Decimal("1000.00"))
        self.assertEqual(service.get_profit_loss(), Decimal("0.00"))


if __name__ == "__main__":
    unittest.main()