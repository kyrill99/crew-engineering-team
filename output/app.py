from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

import gradio as gr

from account_service import AccountService
from factory import AccountServiceFactory
from price_provider import FixedPriceProvider, PriceProvider, PriceProviderError

try:
    from account_state import AccountError, TransactionType
except Exception:
    try:
        from errors import AccountError
    except Exception:
        from models import AccountError, TransactionType  # type: ignore


SUPPORTED_SYMBOLS = ["AAPL", "TSLA", "GOOGL"]


def _fmt_decimal(value: Any) -> str:
    try:
        if value is None:
            return "-"
        if isinstance(value, Decimal):
            return f"{value.quantize(Decimal('0.01')):.2f}"
        return f"{Decimal(str(value)).quantize(Decimal('0.01')):.2f}"
    except Exception:
        return str(value)


def _safe_decimal(text: str) -> Decimal:
    try:
        return Decimal(str(text).strip())
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise AccountError("Invalid numeric value.", "INVALID_VALUE") from exc


def _safe_int(text: str) -> int:
    try:
        value = int(str(text).strip())
    except (ValueError, TypeError) as exc:
        raise AccountError("Invalid integer value.", "INVALID_VALUE") from exc
    return value


def _transaction_to_row(tx: Any) -> List[str]:
    tx_type = getattr(tx, "transaction_type", None)
    timestamp = getattr(tx, "timestamp", None)
    return [
        str(tx_type.value if hasattr(tx_type, "value") else tx_type),
        timestamp.isoformat(sep=" ", timespec="seconds") if timestamp else "-",
        str(getattr(tx, "account_id", "-")),
        _fmt_decimal(getattr(tx, "amount", None)),
        _fmt_decimal(getattr(tx, "symbol", None)),
        str(getattr(tx, "quantity", "-")),
        _fmt_decimal(getattr(tx, "unit_price", None)),
        _fmt_decimal(getattr(tx, "total_amount", None)),
        _fmt_decimal(getattr(tx, "post_cash_balance", None)),
        str(getattr(tx, "post_holding_quantity", "-")),
    ]


def _build_transactions_table(transactions: List[Any]) -> List[List[str]]:
    return [_transaction_to_row(tx) for tx in transactions]


def _get_provider_from_choice(choice: str, custom_prices: Dict[str, Any]) -> PriceProvider:
    if choice == "Fixed test prices":
        return FixedPriceProvider()
    if choice == "Custom prices":
        prices: Dict[str, Decimal] = {}
        for symbol in SUPPORTED_SYMBOLS:
            raw = custom_prices.get(symbol, "").strip()
            if raw:
                prices[symbol] = _safe_decimal(raw)
        if not prices:
            prices = FixedPriceProvider.DEFAULT_PRICES
        return FixedPriceProvider(prices=prices)
    return FixedPriceProvider()


def _ensure_service_state(state: Optional[AccountService]) -> AccountService:
    if state is None:
        raise AccountError("Please create an account first.", "ACCOUNT_NOT_FOUND")
    return state


def create_account(account_id: str, price_mode: str, aapl: str, tsla: str, googl: str):
    custom_prices = {"AAPL": aapl, "TSLA": tsla, "GOOGL": googl}
    provider = _get_provider_from_choice(price_mode, custom_prices)
    factory = AccountServiceFactory()
    service = factory.create_with_price_provider(account_id.strip(), provider)

    holdings = service.get_holdings()
    transactions = service.list_transactions()
    portfolio_value = service.get_portfolio_value()
    profit_loss = service.get_profit_loss()

    return (
        service,
        f"Account created: {account_id.strip()}",
        _summary_text(service, portfolio_value, profit_loss),
        _holdings_text(holdings),
        _build_transactions_table(transactions),
    )


def deposit_funds(service: Optional[AccountService], amount: str):
    service = _ensure_service_state(service)
    tx = service.deposit(_safe_decimal(amount))
    return _post_action_outputs(service, f"Deposited {_fmt_decimal(tx.amount)}")


def withdraw_funds(service: Optional[AccountService], amount: str):
    service = _ensure_service_state(service)
    tx = service.withdraw(_safe_decimal(amount))
    return _post_action_outputs(service, f"Withdrew {_fmt_decimal(tx.amount)}")


def buy_shares(service: Optional[AccountService], symbol: str, quantity: str):
    service = _ensure_service_state(service)
    tx = service.buy_shares(symbol, _safe_int(quantity))
    return _post_action_outputs(
        service,
        f"Bought {tx.quantity} {tx.symbol} at {_fmt_decimal(tx.unit_price)} each",
    )


def sell_shares(service: Optional[AccountService], symbol: str, quantity: str):
    service = _ensure_service_state(service)
    tx = service.sell_shares(symbol, _safe_int(quantity))
    return _post_action_outputs(
        service,
        f"Sold {tx.quantity} {tx.symbol} at {_fmt_decimal(tx.unit_price)} each",
    )


def refresh_reports(service: Optional[AccountService]):
    service = _ensure_service_state(service)
    return _post_action_outputs(service, "Refreshed reports")


def _post_action_outputs(service: AccountService, message: str):
    portfolio_value = service.get_portfolio_value()
    profit_loss = service.get_profit_loss()
    holdings = service.get_holdings()
    transactions = service.list_transactions()

    return (
        service,
        message,
        _summary_text(service, portfolio_value, profit_loss),
        _holdings_text(holdings),
        _build_transactions_table(transactions),
    )


def _summary_text(service: AccountService, portfolio_value: Decimal, profit_loss: Decimal) -> str:
    state = service._require_account()  # demo app; read-only use for display
    cash = getattr(state, "cash_balance", Decimal("0"))
    initial = getattr(state, "initial_deposit_basis", Decimal("0"))
    holdings = getattr(state, "holdings", {})
    holding_count = len(holdings)
    total_shares = sum(int(v) for v in holdings.values())

    return (
        f"Account ID: {state.account_id}\n"
        f"Cash balance: {_fmt_decimal(cash)}\n"
        f"Initial deposit basis: {_fmt_decimal(initial)}\n"
        f"Portfolio value: {_fmt_decimal(portfolio_value)}\n"
        f"Profit / Loss: {_fmt_decimal(profit_loss)}\n"
        f"Held symbols: {holding_count}\n"
        f"Total shares held: {total_shares}"
    )


def _holdings_text(holdings: Dict[str, int]) -> str:
    if not holdings:
        return "No holdings yet."
    lines = ["Current holdings:"]
    for symbol, quantity in sorted(holdings.items()):
        lines.append(f"- {symbol}: {quantity}")
    return "\n".join(lines)


def _bootstrap_demo_service() -> AccountService:
    factory = AccountServiceFactory()
    return factory.create_with_fixed_prices("demo-user")


with gr.Blocks(title="Trading Simulation Account Demo") as demo:
    gr.Markdown(
        "# Trading Simulation Account Demo\n"
        "Simple prototype for account creation, cash management, trading, and reporting.\n"
        "This demo assumes a single user and uses fixed test prices for AAPL, TSLA, and GOOGL by default."
    )

    service_state = gr.State(value=None)

    with gr.Row():
        account_id = gr.Textbox(label="Account ID", value="demo-user")
        price_mode = gr.Dropdown(
            label="Price Provider",
            choices=["Fixed test prices", "Custom prices"],
            value="Fixed test prices",
        )

    with gr.Accordion("Optional custom fixed prices", open=False):
        gr.Markdown("Used only if Price Provider is set to Custom prices.")
        with gr.Row():
            aapl_price = gr.Textbox(label="AAPL", value="190.00")
            tsla_price = gr.Textbox(label="TSLA", value="250.00")
            googl_price = gr.Textbox(label="GOOGL", value="140.00")

    with gr.Row():
        create_btn = gr.Button("Create / Reset Account", variant="primary")
        refresh_btn = gr.Button("Refresh Reports")

    status = gr.Textbox(label="Status", interactive=False)
    summary = gr.Textbox(label="Account Summary", lines=7, interactive=False)
    holdings = gr.Textbox(label="Holdings", lines=6, interactive=False)

    transactions = gr.Dataframe(
        headers=[
            "Type",
            "Timestamp",
            "Account",
            "Amount",
            "Symbol",
            "Quantity",
            "Unit Price",
            "Total",
            "Post Cash",
            "Post Holding Qty",
        ],
        datatype=["str"] * 10,
        label="Transaction History",
        interactive=False,
        wrap=True,
    )

    gr.Markdown("## Actions")

    with gr.Row():
        deposit_amount = gr.Textbox(label="Deposit Amount", value="1000")
        withdraw_amount = gr.Textbox(label="Withdraw Amount", value="100")

    with gr.Row():
        deposit_btn = gr.Button("Deposit")
        withdraw_btn = gr.Button("Withdraw")

    with gr.Row():
        trade_symbol = gr.Dropdown(label="Symbol", choices=SUPPORTED_SYMBOLS, value="AAPL")
        trade_quantity = gr.Textbox(label="Quantity", value="1")

    with gr.Row():
        buy_btn = gr.Button("Buy Shares", variant="primary")
        sell_btn = gr.Button("Sell Shares")

    def _create_wrapper(account_id, price_mode, aapl, tsla, googl):
        try:
            return create_account(account_id, price_mode, aapl, tsla, googl)
        except Exception as exc:
            return (
                None,
                f"Error: {exc}",
                "",
                "",
                [],
            )

    def _deposit_wrapper(service, amount):
        try:
            return deposit_funds(service, amount)
        except Exception as exc:
            return (
                service,
                f"Error: {exc}",
                "",
                "",
                _build_transactions_table(service.list_transactions()) if service else [],
            )

    def _withdraw_wrapper(service, amount):
        try:
            return withdraw_funds(service, amount)
        except Exception as exc:
            return (
                service,
                f"Error: {exc}",
                "",
                "",
                _build_transactions_table(service.list_transactions()) if service else [],
            )

    def _buy_wrapper(service, symbol, quantity):
        try:
            return buy_shares(service, symbol, quantity)
        except Exception as exc:
            return (
                service,
                f"Error: {exc}",
                "",
                "",
                _build_transactions_table(service.list_transactions()) if service else [],
            )

    def _sell_wrapper(service, symbol, quantity):
        try:
            return sell_shares(service, symbol, quantity)
        except Exception as exc:
            return (
                service,
                f"Error: {exc}",
                "",
                "",
                _build_transactions_table(service.list_transactions()) if service else [],
            )

    def _refresh_wrapper(service):
        try:
            return refresh_reports(service)
        except Exception as exc:
            return (
                service,
                f"Error: {exc}",
                "",
                "",
                _build_transactions_table(service.list_transactions()) if service else [],
            )

    create_btn.click(
        _create_wrapper,
        inputs=[account_id, price_mode, aapl_price, tsla_price, googl_price],
        outputs=[service_state, status, summary, holdings, transactions],
    )

    deposit_btn.click(
        _deposit_wrapper,
        inputs=[service_state, deposit_amount],
        outputs=[service_state, status, summary, holdings, transactions],
    )

    withdraw_btn.click(
        _withdraw_wrapper,
        inputs=[service_state, withdraw_amount],
        outputs=[service_state, status, summary, holdings, transactions],
    )

    buy_btn.click(
        _buy_wrapper,
        inputs=[service_state, trade_symbol, trade_quantity],
        outputs=[service_state, status, summary, holdings, transactions],
    )

    sell_btn.click(
        _sell_wrapper,
        inputs=[service_state, trade_symbol, trade_quantity],
        outputs=[service_state, status, summary, holdings, transactions],
    )

    refresh_btn.click(
        _refresh_wrapper,
        inputs=[service_state],
        outputs=[service_state, status, summary, holdings, transactions],
    )

    demo.load(
        lambda: _bootstrap_demo_service(),
        inputs=None,
        outputs=service_state,
    )

if __name__ == "__main__":
    demo.queue()
    demo.launch()