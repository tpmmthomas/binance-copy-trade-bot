import pymongo
import pandas as pd
import time
import logging
from pybit.usdt_perpetual import HTTP

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class dbOperations:
    def __init__(self, glb, udt):
        self.globals = glb
        self.client = pymongo.MongoClient(glb.dbpath)
        self.db = self.client["binance"]
        self.usertable = self.db["Users"]
        self.commandtable = self.db["Commands"]
        self.tradertable = self.db["Traders"]
        self.notitable = self.db["Notifications"]
        self.updater = udt

    def getall(self, table):
        data = []
        if table == "usertable":
            for x in self.usertable.find():
                data.append(x)
        if table == "commandtable":
            for x in self.commandtable.find():
                data.append(x)
        return data

    def delete_command(self, docids):
        for docid in docids:
            self.commandtable.delete_one({"_id": docid})

    def add_user(self, chat_id, userdoc):
        self.usertable.insert_one(userdoc)
        self.updater.bot.sendMessage(chat_id, "Initialization successful!")

    def get_trader(self, name):
        myquery = {"name": name}
        return self.tradertable.find_one(myquery)

    def add_trader(self, traderdoc):
        self.tradertable.insert_one(traderdoc)

    def get_user(self, chat_id):
        myquery = {"chat_id": chat_id}
        return self.usertable.find_one(myquery)

    def update_user(self, chat_id, userdoc):
        myquery = {"chat_id": chat_id}
        return self.usertable.replace_one(myquery, userdoc)

    def update_trader(self, uid, traderdoc):
        myquery = {"uid": uid}
        return self.tradertable.replace_one(myquery, traderdoc)

    def check_presence(self, chat_id):
        myquery = {"chat_id": chat_id}
        mydoc = self.usertable.find(myquery)
        i = 0
        for doc in mydoc:
            i += 1
        return i >= 1

    def deleteuser(self, chat_id):
        myquery = {"chat_id": chat_id}
        user = self.usertable.find_one(myquery)
        for uid in user["traders"]:
            self.delete_trader(uid)
        self.usertable.delete_many(myquery)
        self.updater.bot.sendMessage(chat_id, "Account successfully deleted.")

    def get_trader_list(self, chat_id):
        myquery = {"chat_id": chat_id}
        user = self.usertable.find_one(myquery)
        data = []
        for x in user["traders"]:
            data.append(user["traders"][x]["name"])
        return data

    def get_trader_fromuser(self, chat_id, tradername):
        myquery = {"chat_id": chat_id}
        user = self.usertable.find_one(myquery)
        for uid in user["traders"]:
            if user["traders"][uid]["name"] == tradername:
                return user["traders"][uid]
        return None

    def delete_trader(self, uid, chat_id=None):
        myquery = {"uid": uid}
        data = self.tradertable.find_one(myquery)
        if data["num_followed"] == 1:
            self.tradertable.delete_one(myquery)
        else:
            data["num_followed"] -= 1
            self.tradertable.replace_one(myquery, data)
        if chat_id is not None:
            user = self.get_user(chat_id)
            del user["traders"][uid]
            myquery = {"chat_id": chat_id}
            self.usertable.replace_one(myquery, user)

    def insert_notification(self, noti):
        self.notitable.insert_one(noti)

    def set_all_leverage(self, chat_id, lev):
        myquery = {"chat_id": chat_id}
        data = self.usertable.find_one(myquery)
        temp = dict()
        for symbol in data["leverage"]:
            temp[f"leverage.{symbol}"] = lev
        newvalues = {"$set": temp}
        self.usertable.update_one(myquery, newvalues)
        self.updater.bot.sendMessage(chat_id, "successfully updated leverage!")

    def get_user_symbols(self, chat_id):
        myquery = {"chat_id": chat_id}
        data = self.usertable.find_one(myquery)
        return list(data["leverage"].keys())

    def set_leverage(self, chat_id, symbol, lev):
        myquery = {"chat_id": chat_id}
        newvalues = {"$set": {f"leverage.{symbol}": lev}}
        self.usertable.update_one(myquery, newvalues)
        self.updater.bot.sendMessage(chat_id, "successfully updated leverage!")

    def list_followed_traders(self, chat_id):
        myquery = {"chat_id": chat_id}
        data = self.usertable.find_one(myquery)
        traderlist = []
        for uid in data["traders"]:
            traderlist.append(data["traders"][uid]["name"])
        return traderlist

    def set_all_proportion(self, chat_id, uid, prop):
        myquery = {"chat_id": chat_id}
        data = self.usertable.find_one(myquery)
        temp = dict()
        for symbol in data["traders"][uid]["proportion"]:
            temp[f"traders.{uid}.proportion.{symbol}"] = prop
        newvalues = {"$set": temp}
        self.usertable.update_many(myquery, newvalues)

    def set_proportion(self, chat_id, uid, symbol, prop):
        myquery = {"chat_id": chat_id}
        newvalues = {"$set": {f"traders.{uid}.proportion.{symbol}": prop}}
        self.usertable.update_one(myquery, newvalues)
        self.updater.bot.sendMessage(chat_id, "Successfully changed proportion!")

    def query_field(self, chat_id, *args):
        myquery = {"chat_id": chat_id}
        result = self.usertable.find_one(myquery)
        for key in list(args):
            result = result[key]
        return result

    def set_all_tmode(self, chat_id, uid, tmode):
        myquery = {"chat_id": chat_id}
        data = self.usertable.find_one(myquery)
        temp = dict()
        for symbol in data["traders"][uid]["tmode"]:
            temp[f"traders.{uid}.tmode.{symbol}"] = tmode
        newvalues = {"$set": temp}
        self.usertable.update_many(myquery, newvalues)

    def set_tmode(self, chat_id, uid, symbol, tmode):
        myquery = {"chat_id": chat_id}
        newvalues = {"$set": {f"traders.{uid}.tmode.{symbol}": tmode}}
        self.usertable.update_one(myquery, newvalues)

    def set_safety(self, chat_id, sr):
        myquery = {"chat_id": chat_id}
        newvalues = {"$set": {f"safety_ratio": sr}}
        self.usertable.update_one(myquery, newvalues)

    def set_slippage(self, chat_id, sr):
        myquery = {"chat_id": chat_id}
        newvalues = {"$set": {f"slippage": sr}}
        self.usertable.update_one(myquery, newvalues)

    def set_api(self, chat_id, key, secret):
        myquery = {"chat_id": chat_id}
        newvalues = {"$set": {f"api_key": key, "api_secret": secret}}
        self.usertable.update_one(myquery, newvalues)

    def get_balance(self, chat_id):
        result = self.usertable.find_one({"chat_id": chat_id})
        try:
            client = HTTP(
                endpoint="https://api.bybit.com", api_key=result["api_key"], api_secret=result["api_secret"]
            )
            result = client.get_wallet_balance(coin="USDT")
            result = result["result"]["USDT"]
            tosend = f"Your USDT account balance:\nBalance: {result['equity']}\nAvailable: {result['available_balance']}\nRealised PNL: {result['realised_pnl']}\nUnrealized PNL: {result['unrealised_pnl']}"
            self.updater.bot.sendMessage(chat_id=chat_id, text=tosend)
        except Exception as e:
            logger.info(str(e))
            self.updater.bot.sendMessage(
                chat_id=chat_id, text="Unable to retrieve balance."
            )

    def get_positions(self, chat_id):
        result = self.usertable.find_one({"chat_id": chat_id})
        try:
            client = HTTP(
                endpoint="https://api.bybit.com", api_key=result["api_key"], api_secret=result["api_secret"]
            )
            result = client.my_position()['result']
        except:
            logger.error("Other errors")
        try:
            symbol = []
            size = []
            EnPrice = []
            MarkPrice = []
            PNL = []
            margin = []
            for pos in result:
                pos = pos["data"]
                if float(pos["size"]) != 0:
                    try:
                        mp = client.public_trading_records(symbol=pos['symbol'],limit=1)['result'][0]['price']
                    except:
                        mp = pos["entry_price"]
                    symbol.append(pos["symbol"])
                    tsize = pos["size"]
                    tsize = tsize if pos["side"] == "Buy" else -tsize
                    size.append(tsize)
                    EnPrice.append(pos["entry_price"])
                    MarkPrice.append(mp)
                    PNL.append(pos["unrealised_pnl"])
                    margin.append(pos["leverage"])
            newPosition = pd.DataFrame(
                {
                    "symbol": symbol,
                    "size": size,
                    "Entry Price": EnPrice,
                    "Mark Price": MarkPrice,
                    "PNL": PNL,
                    "leverage": margin,
                }
            )
            numrows = newPosition.shape[0]
            if numrows <= 10:
                tosend = (
                    f"Your current Position: " + "\n" + newPosition.to_string() + "\n"
                )
                self.updater.bot.sendMessage(chat_id=chat_id, text=tosend)
            else:
                firstdf = newPosition.iloc[0:10]
                tosend = (
                    f"Your current Position: "
                    + "\n"
                    + firstdf.to_string()
                    + "\n(cont...)"
                )
                self.updater.bot.sendMessage(chat_id=chat_id, text=tosend)
                for i in range(numrows // 10):
                    seconddf = newPosition.iloc[
                        (i + 1) * 10 : min(numrows, (i + 2) * 10)
                    ]
                    if not seconddf.empty:
                        self.updater.bot.sendMessage(
                            chat_id=chat_id, text=seconddf.to_string()
                        )
        except Exception as e:
            logger.info(f"hi {str(e)}")
            self.updater.bot.sendMessage(chat_id, "Unable to get positions.")
        return
