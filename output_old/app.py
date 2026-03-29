import gradio as gr
from accounts import Account, AccountError, InsufficientFundsError, InsufficientHoldingsError, UnknownSymbolError

# Create a single user account for demonstration
account = Account(account_id="123456", owner_name="Demo User")

def create_account(owner_name):
    global account
    account = Account(account_id="123456", owner_name=owner_name)
    return f"Account created for {owner_name}"

def deposit_funds(amount):
    try:
        account.deposit(float(amount))
        return f"Deposited {amount}. Current balance: {account.get_cash_balance()}"
    except AccountError as e:
        return str(e)

def withdraw_funds(amount):
    try:
        account.withdraw(float(amount))
        return f"Withdrew {amount}. Current balance: {account.get_cash_balance()}"
    except AccountError as e:
        return str(e)
    
def buy_shares(symbol, quantity):
    try:
        account.buy_shares(symbol, int(quantity))
        return f"Bought {quantity} shares of {symbol}. Holdings: {account.get_holdings()}"
    except AccountError as e:
        return str(e)

def sell_shares(symbol, quantity):
    try:
        account.sell_shares(symbol, int(quantity))
        return f"Sold {quantity} shares of {symbol}. Holdings: {account.get_holdings()}"
    except AccountError as e:
        return str(e)

def get_portfolio_value():
    return f"Total portfolio value: {account.get_portfolio_value()}"

def get_profit_loss():
    return f"Profit/Loss: {account.get_profit_loss()}"

def get_holdings():
    return f"Holdings: {account.get_holdings()}"

def get_transaction_history():
    history = "\n".join([str(txn.to_dict()) for txn in account.get_transaction_history()])
    return f"Transaction history:\n{history}"

with gr.Blocks() as demo:
    gr.Markdown("## Trading Simulation Platform")

    with gr.Tab("Account"):
        owner_name_input = gr.Textbox(label="Owner Name", placeholder="Enter owner name")
        create_button = gr.Button("Create Account")
        create_result = gr.Textbox(label="Result")
        create_button.click(fn=create_account, inputs=owner_name_input, outputs=create_result)
        
        deposit_input = gr.Number(label="Deposit Amount", value=0.0)
        deposit_button = gr.Button("Deposit")
        deposit_result = gr.Textbox(label="Deposit Result")
        deposit_button.click(fn=deposit_funds, inputs=deposit_input, outputs=deposit_result)
        
        withdraw_input = gr.Number(label="Withdraw Amount", value=0.0)
        withdraw_button = gr.Button("Withdraw")
        withdraw_result = gr.Textbox(label="Withdraw Result")
        withdraw_button.click(fn=withdraw_funds, inputs=withdraw_input, outputs=withdraw_result)
    
    with gr.Tab("Trade"):
        buy_symbol_input = gr.Textbox(label="Buy Symbol", placeholder="AAPL, TSLA, GOOGL")
        buy_quantity_input = gr.Number(label="Quantity", value=1, precision=0)
        buy_button = gr.Button("Buy Shares")
        buy_result = gr.Textbox(label="Buy Result")
        buy_button.click(fn=buy_shares, inputs=[buy_symbol_input, buy_quantity_input], outputs=buy_result)
        
        sell_symbol_input = gr.Textbox(label="Sell Symbol", placeholder="AAPL, TSLA, GOOGL")
        sell_quantity_input = gr.Number(label="Quantity", value=1, precision=0)
        sell_button = gr.Button("Sell Shares")
        sell_result = gr.Textbox(label="Sell Result")
        sell_button.click(fn=sell_shares, inputs=[sell_symbol_input, sell_quantity_input], outputs=sell_result)
    
    with gr.Tab("Reports"):
        portfolio_value_button = gr.Button("Get Portfolio Value")
        portfolio_value_result = gr.Textbox(label="Portfolio Value")
        portfolio_value_button.click(fn=get_portfolio_value, outputs=portfolio_value_result)
        
        profit_loss_button = gr.Button("Get Profit/Loss")
        profit_loss_result = gr.Textbox(label="Profit/Loss")
        profit_loss_button.click(fn=get_profit_loss, outputs=profit_loss_result)

        holdings_button = gr.Button("Get Holdings")
        holdings_result = gr.Textbox(label="Holdings")
        holdings_button.click(fn=get_holdings, outputs=holdings_result)
        
        transaction_history_button = gr.Button("Get Transaction History")
        transaction_history_result = gr.Textbox(label="Transaction History")
        transaction_history_button.click(fn=get_transaction_history, outputs=transaction_history_result)

demo.launch()