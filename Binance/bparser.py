from binance.helpers import round_step_size
import configparser
import requests
import disbot
import datetime


config = configparser.ConfigParser()
config.read('config.ini')


def isLeverageValid(symbol, leverage):
    bracket = client.futures_leverage_bracket(symbol=symbol)
    return any(bracketInfo['initialLeverage'] > int(leverage) for bracketInfo in bracket[0]["brackets"])


def isSymbolValid(symbol):
    bracket = client.futures_exchange_info()
    return any(symbolInfo['symbol'] == symbol for symbolInfo in bracket['symbols'])


def login():
    global client
    from assist import client
    global db
    import db


def aBalance():
    balance = client.futures_account_balance()
    return {item["asset"]: float(item["balance"]) for item in balance if float(item["balance"]) != 0}


def leverage(trade):
    mode = config['other-settings']['mode']

    lev = db.getLeverage(trade['symbol'])
    if lev != 0 and mode == str(1):
        return lev
    elif mode == str(2) or mode == str(3):
        dLeverage = config['other-settings']['default-leverage']
        return int(dLeverage)
    else:
        return trade['leverage']


def account():
    client.futures_account()


def aQty(symbol):
    balance = client.futures_account_balance()
    qty = next((float(item["balance"])
               for item in balance if item["asset"] == symbol), None)
    return qty


def convert(qty, trade):
    symbol = trade['symbol']
    tick_info = client.futures_exchange_info()
    symbol_info = next(
        info for info in tick_info["symbols"] if info["symbol"] == symbol)

    quote_symbol = symbol_info["quoteAsset"]
    base_symbol = symbol_info["baseAsset"]

    url = f"https://min-api.cryptocompare.com/data/price?fsym={quote_symbol}&tsyms={base_symbol}"
    response = requests.get(url)
    data = response.json()
    rate = data[base_symbol]
    converted = qty * rate

    return converted


def round_tick(amount, symbol):
    tick_info = client.futures_exchange_info()
    symbol_info = next(
        info for info in tick_info["symbols"] if info["symbol"] == symbol)
    step_size = next(d['stepSize']
                     for d in symbol_info['filters'] if 'stepSize' in d)
    return round_step_size(float(amount), float(step_size))


def setQty(trade, leverage):
    config = configparser.ConfigParser()
    config.read('config.ini')
    percent = int(config['other-settings']['percent'])
    tick_info = client.futures_exchange_info()
    symbol_info = next(
        info for info in tick_info["symbols"] if info["symbol"] == trade['symbol'])
    step_size = next(d['stepSize']
                     for d in symbol_info['filters'] if 'stepSize' in d)
    base_currency = trade['symbol'][-4:]
    balance = aQty(base_currency)
    if balance < 1:
        return
    qty = (balance * percent / 100) * leverage

    qty_converted = convert(qty, trade)
    fQty = round_step_size(float(qty_converted), float(step_size))
    return fQty


def set_tp_sl(trade, tp_percent, sl_percent, leverage):
    tick_info = client.futures_exchange_info()
    symbol_info = next(
        info for info in tick_info["symbols"] if info["symbol"] == trade["symbol"])
    tick_size = float(symbol_info["filters"][0]["tickSize"])

    entry_price = float(trade['entryPrice'])
    tp = round_step_size(entry_price * (1 + tp_percent / 100) / leverage,
                         tick_size) if trade["amount"] > 0 else round_step_size(entry_price * (1 - tp_percent / 100) / leverage, tick_size)
    sl = round_step_size(entry_price * (1 - sl_percent / 100) / leverage,
                         tick_size) if trade["amount"] > 0 else round_step_size(entry_price * (1 + sl_percent / 100) / leverage, tick_size)
    return tp, sl


def stats():
    now = int(datetime.datetime.now().timestamp()) * 1000
    end_time = now
    start_time_24h = now - 86400000
    start_time_week = now - 604800000
    start_time_month = now - 2592000000

    income_list_24h = client.futures_income_history(
        incomeType="REALIZED_PNL", startTime=start_time_24h, endTime=end_time)
    income_list_week = client.futures_income_history(
        incomeType="REALIZED_PNL", startTime=start_time_week, endTime=end_time)
    income_list_month = client.futures_income_history(
        incomeType="REALIZED_PNL", startTime=start_time_month, endTime=end_time)

    income_total_24h = sum(float(item['income']) for item in income_list_24h)
    income_total_week = sum(float(item['income']) for item in income_list_week)
    income_total_month = sum(float(item['income'])
                             for item in income_list_month)

    return (round(income_total_24h, 2), round(income_total_week, 2), round(income_total_month, 2))


def pnlRoe(symbol):
    symbol = symbol[-4:]
    account = client.futures_account()

    for asset_info in account['assets']:
        if asset_info['asset'] == symbol:
            initial_margin = float(asset_info['initialMargin'])
            unrealized_profit = float(asset_info['unrealizedProfit'])
            pnl = float(asset_info['crossUnPnl'])
            roe = unrealized_profit / initial_margin * 100

            return pnl, round(roe, 2)
    return None


def close_position_market_price(tSymbol, nickname, side):
    symbol = tSymbol
    position_info = client.futures_position_information(symbol=symbol)
    position_quantity = float(position_info[0]["positionAmt"])

    data = pnlRoe(symbol)
    try:
        response = client.futures_create_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=abs(position_quantity)
        )
        disbot.webhook_end(
            "❌ Clotured Trade : " + nickname if float(
                position_info[0]["unRealizedProfit"]) < 0 else "✅ Clotured Trade : " + nickname,
            position_info[0]["symbol"],
            position_info[0]["leverage"],
            position_info[0]["entryPrice"],
            position_info[0]["markPrice"],
            data,
            "f55142" if float(
                position_info[0]["unRealizedProfit"]) < 0 else "42f5b9"
        )
    except Exception as e:
        disbot.webhook_error("Order not cancelled", symbol)


def sell_all_market_price(tSymbol, nickname):
    close_position_market_price(tSymbol, nickname, side="SELL")


def buy_all_market_price(tSymbol, nickname):
    close_position_market_price(tSymbol, nickname, side="BUY")


def getCurrentTrade():
    trades = []
    trade = client.futures_position_information()
    for i in trade:
        if float(i["positionAmt"]) != 0:
            trades.append(i)
    return trades


def setBreakEven(arg):
    entryPrice = getEntryPrice(arg)
    position_info = client.futures_position_information(symbol=arg)
    position_quantity = float(position_info[0]["positionAmt"])
    try:
        stop_market = client.futures_create_order(
            symbol=arg,
            side="SELL",
            type="STOP_MARKET",
            quantity=abs(position_quantity),
            stopPrice=entryPrice,
            reduceOnly=True
        )
        return True
    except Exception:
        return False


def getEntryPrice(symbol):
    trade = client.futures_position_information()
    for i in trade:
        if i["symbol"] == symbol:
            return i["entryPrice"]


def create_trade(trade, nickname):
    leveragee = leverage(trade)
    quantity = setQty(trade, leveragee)
    marginType = "ISOLATED"

    config = configparser.ConfigParser()
    config.read('config.ini')

    if config['other-settings']['TP'] != "0" and config['other-settings']['SL'] != "0" and config['other-settings']['TPSL'] == "True":
        tp_percent = float(config['other-settings']['TP'])
        sl_percent = float(config['other-settings']['SL'])

        tp, sl = set_tp_sl(trade, tp_percent, sl_percent, leveragee)

        tpsl = True

    try:
        client.futures_change_leverage(
            symbol=trade['symbol'], leverage=leveragee)
        client.futures_change_margin_type(
            symbol=trade['symbol'], marginType=marginType)
    except:
        pass

    try:
        side = "BUY" if trade["amount"] > 0 else "SELL"
        response = client.futures_create_order(
            symbol=trade['symbol'],
            side=side,
            type="MARKET",
            quantity=abs(quantity),
        )

        disbot.webhook_start("♻️ New Followed Trade : " + nickname, side,
                             trade['symbol'], response["orderId"], response["origQty"], leveragee, trade['entryPrice'], "FFDEAD")

        if config['other-settings']['TP'] != "0" and config['other-settings']['SL'] != "0" and config['other-settings']['TPSL'] == "True":
            tp_percent = float(config['other-settings']['TP'])
            sl_percent = float(config['other-settings']['SL'])

            tp, sl = set_tp_sl(trade, tp_percent, sl_percent, leveragee)
            TpSl(trade, quantity, tp, sl)

        return response

    except Exception as e:
        handle_error(e, trade)


def TpSl(trade, quantity, tp, sl):
    try:
        order_params = {
            "symbol": trade['symbol'],
            "side": "SELL" if trade["amount"] > 0 else "BUY",
            "quantity": abs(quantity),
            "workingType": "MARK_PRICE",
            "reduceOnly": "true"
        }
        client.futures_create_order(
            **order_params, type="TAKE_PROFIT_MARKET", stopPrice=tp)
        client.futures_create_order(
            **order_params, type="STOP_MARKET", stopPrice=sl)

    except Exception as e:
        handle_error(e, trade)


def margin_update(trade, margin, mode, md, nickname, percent):
    quantity = round_tick(margin, trade['symbol'])
    leveragee = leverage(trade)

    side = "SELL" if (mode == 0 and md == 1) or (
        mode == 1 and md == 0) else "BUY"

    try:
        response = client.futures_create_order(
            symbol=trade['symbol'],
            side=side,
            type="MARKET",
            quantity=abs(quantity),
        )

        disbot.webhook_infos("🔼 Augmented Trade : " + nickname if mode == 1 else "🔽 Reduced Trade : " + nickname,
                             side, trade['symbol'], response["orderId"], response["origQty"], leveragee, percent, "4287f5")
        position_info = client.futures_position_information(
            symbol=trade['symbol'])
        position_quantity = float(position_info[0]["positionAmt"])

        return position_quantity
    except Exception as e:
        handle_error(e, trade)


def handle_error(e, trade):
    if str(e) == "APIError(code=-2019): Margin is insufficient.":
        disbot.webhook_error("Margin is insufficient", trade['symbol'])
    elif str(e) == "APIError(code=-2010): Account has insufficient balance for requested action.":
        disbot.webhook_error(
            "Account has insufficient balance for requested action", trade['symbol'])
    elif str(e) == "APIError(code=-2021): Order would immediately trigger.":
        disbot.webhook_error(
            "Order would immediately trigger", trade['symbol'])
    elif str(e) == "APIError(code=-4164): Order's notional must be no smaller than 5.0 (unless you choose reduce only)":
        disbot.webhook_error(
            "Order's notional must be no smaller than 5.0", trade['symbol'])
    elif str(e) == "APIError(code=-4003): Quantity less than or equal to zero.":
        disbot.webhook_error(
            "Quantity less than or equal to zero.", trade['symbol'])
    else:
        print(e)
