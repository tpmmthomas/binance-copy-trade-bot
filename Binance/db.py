import requests
import configparser
import pymongo
import threading
import certifi
import bparser
from time import sleep


ca = certifi.where()

config = configparser.ConfigParser()
config.read('config.ini')
cluster = pymongo.MongoClient(config["mongo-server"]["url"], tlsCAFile=ca)

db = cluster["traders"]
followedTraders = db["followedTraders"]
positions = db["positions"]
followedTrades = db["openTrades"]
leverages = db["leverages"]


def setLeverage(symbol, leverage):
    leverages.replace_one({"symbol": symbol}, {
                          "symbol": symbol, "leverage": leverage}, upsert=True)


def retrieveUserName(uid):
    try:
        r = requests.post(
            "https://www.binance.com/bapi/futures/v2/public/future/leaderboard/getOtherLeaderboardBaseInfo", json={"encryptedUid": uid})
        assert r.status_code == 200
        return r.json()['data']['nickName']
    except Exception:
        return None


def retrieveLastPositions(uid):
    try:
        r = requests.post("https://www.binance.com/bapi/futures/v1/public/future/leaderboard/getOtherPosition",
                          json={"encryptedUid": uid, "tradeType": "PERPETUAL"})
        return r.json()['data']['otherPositionRetList']
    except Exception:
        print("Error retrieving positions")


def updateTrades():
    cursor = followedTraders.find({})
    if not cursor:
        return "Oops, you don't have any traders yet !"

    for uid in cursor:
        lTrades = retrieveLastPositions(uid['uid'])
        nickName = retrieveUserName(uid['uid'])
        if lTrades and len(lTrades) > 0:
            positions.replace_one({"Trader": nickName}, {
                                  "Trader": nickName, "trades": lTrades}, upsert=True)


def freeDB():
    positions.delete_many({})


def deleteTraders(values):
    try:
        followedTraders.delete_many({"Trader": {'$in': values}})
        positions.delete_many({"Trader": {'$in': values}})
        return "Successfully deleted."
    except Exception:
        return "Oops ! Something went wrong."


def myTrades():
    cursor = followedTrades.find({})
    for trade in cursor:
        trades = client.futures_account_trades(symbol=trade['symbol'])
        position_amt = float(trades[0]['positionAmt'])
        if position_amt == 0:
            followedTrades.find_one_and_delete({"symbol": trade['symbol']})
        else:
            pass


def updateNew():
    global client
    from assist import client
    cursor = followedTraders.find({})
    myTrades()
    if not cursor:
        pass

    for uid in cursor:
        lTrades = retrieveLastPositions(uid['uid'])
        nickName = retrieveUserName(uid['uid'])

        existingTrades = positions.find_one({"Trader": nickName})
        openTrades = followedTrades.find({})

        symbols = {item['symbol'] for item in lTrades}

        close_existing_trades(symbols, openTrades, nickName)

        if existingTrades is None:
            insert_new_trades(lTrades, nickName)
        else:
            update_existing_trades(lTrades, existingTrades, nickName)


def close_existing_trades(symbols, openTrades, nickName):
    for trade in openTrades:
        symbol = trade['symbol']
        if symbol not in symbols and trade['Trader'] == nickName:
            followedTrades.find_one_and_delete({"symbol": symbol})
            if trade['type'] == "buy":
                bparser.sell_all_market_price(symbol, nickName)
            else:
                bparser.buy_all_market_price(symbol, nickName)
            print(f"Trade closed: {symbol} for {nickName}")


def insert_new_trades(lTrades, nickName):
    positions.replace_one(
        {"Trader": nickName},
        {"Trader": nickName, "trades": lTrades},
        upsert=True
    )

    existingTrades = positions.find_one({"Trader": nickName})
    nTrade = existingTrades['trades']


def update_existing_trades(lTrades, existingTrades, nickName):
    existingTrades = existingTrades['trades']

    lTradesCopy = lTrades.copy()

    for trade in lTradesCopy:
        symbol = trade['symbol']
        existingTrade = next(
            (t for t in existingTrades if t['symbol'] == symbol), None)

        if existingTrade is None:
            add_new_trade(trade, nickName, existingTrades)
        else:
            update_trade(trade, existingTrade, nickName)

    positions.replace_one(
        {"Trader": nickName},
        {"Trader": nickName, "trades": lTrades},
        upsert=True
    )


def add_new_trade(trade, nickName, existingTrades):
    type = "buy" if trade['amount'] > 0 else "sell"
    existingTrades.append(trade)
    print(f"new trade detected: {trade['symbol']} for {nickName}")
    n = followedTrades.find({})
    number_of_threads = len(list(n.clone()))

    if int(config['other-settings']['maxtrades']) == -1 or number_of_threads <= int(config['other-settings']['maxtrades']):

        trade_followed = bparser.create_trade(trade, nickName)

        try:
            followedTrades.insert_one(
                {
                    "Trader": nickName,
                    "symbol": trade_followed['symbol'],
                    "amount": -float(trade_followed['origQty']) if type == "sell" else float(trade_followed['origQty']),
                    "type": type,
                }
            )
        except Exception as e:
            pass


def update_trade(trade, existingTrade, nickName):
    tmode = config["other-settings"]["mode"]
    symbol = trade['symbol']
    qty = followedTrades.find_one({"symbol": symbol, "Trader": nickName})

    if trade['amount'] != existingTrade['amount'] and qty:
        diff = trade['amount'] - existingTrade['amount']
        percent = abs(diff) / abs(existingTrade['amount']) * 100
        amount = float(qty['amount']) * percent / 100

        if amount != 0 and int(tmode) == 1 or int(tmode) == 2:
            resp = bparser.margin_update(trade, amount, 0 if abs(trade['amount']) < abs(
                existingTrade['amount']) else 1, 1 if trade['amount'] > 0 else 0, nickName, percent)

            followedTrades.find_one_and_update(
                {"symbol": symbol},
                {"$set": {"amount": float(resp)}}
            )
        else:
            close_existing_trades({symbol}, followedTrades.find({}), nickName)

    existingTrade.update(trade)


def getTraders():
    cursor = followedTraders.find({})
    traderList = [document['Trader'] for document in cursor]
    size = len(list(cursor.clone()))
    return False if size == 0 else (size, traderList)


def getLeverage(symbol):
    cursor = leverages.find_one({"symbol": symbol})
    return 0 if cursor is None else cursor['leverage']


def followTrader(uid):
    nickName = retrieveUserName(uid)
    checkIfExist = followedTraders.find_one({'uid': uid})

    if nickName is None:
        return "Oops, please check if your UID is correct !"
    if checkIfExist is not None:
        return f"Oops ! {nickName} is already in your list."
    try:
        followedTraders.insert_one({"Trader": nickName, "uid": uid})
        updateTrades()
        return f"{nickName} was added to your list."
    except Exception as e:
        print(e)
        return "Oops ! Please try again."


def get_stats():
    cursor = followedTrades.find({})
    stats = [document for document in cursor]
    return None if len(stats) == 0 else stats[0]


def update():
    while True:
        try:
            updateNew()
            sleep(10)
        except Exception as e:
            print(e)
            sleep(10)
            continue


thread = threading.Thread(target=update)
thread.start()
