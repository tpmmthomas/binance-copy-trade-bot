from datetime import datetime, timedelta
from datetime import time as timed
import math
import threading
import logging
from app.copy_trade_backend.ct_bybit import BybitClient
import time
from pybit.usdt_perpetual import HTTP
import pandas as pd
import urllib.parse
from app.data.credentials import db_user, db_pw

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class ctGlobal:
    def __init__(self):
        self.stopevent = threading.Event()
        self.dblock = threading.Lock()
        self.apilock = threading.Lock()
        self.past_balances = dict()
        self.has_announced = dict()
        username = urllib.parse.quote_plus(db_user)
        password = urllib.parse.quote_plus(db_pw)
        self.dbpath = "mongodb://%s:%s@localhost:27017/" % (username, password)
        logger.info(self.dbpath)
        return

    def round_up(self, n, decimals=0):
        multiplier = 10**decimals
        return math.ceil(n * multiplier) / multiplier

    def reload_symbols(self, userdb):
        client = HTTP(
            "https://api.bybit.com",
            api_key="",
            api_secret="",
            request_timeout=40,
        )
        res = client.query_symbol()
        for user in userdb.retrieve_users():
            new_lev = {}
            for sym in res['result']:
                if sym['name'] == "ret_code":
                    logger.info("LARGE ERROR! WHY RET_CODE IN HERE")
                    new_lev = user["leverage"]
                    break
                if sym['name'] in user["leverage"]:
                    new_lev[sym['name'] ] = user["leverage"][sym['name'] ]
                else:
                    new_lev[sym['name'] ] = user["leverage"]["XRPUSDT"]
                    userdb.insert_command(
                        {
                            "cmd": "send_message",
                            "chat_id": user["chat_id"],
                            "message": f"There is a new symbol {sym['name']} available, you might want to adjust its settings.",
                        }
                    )
            userdb.update_leverage(user["chat_id"], new_lev)
            for trader in user["traders"]:
                new_prop = {}
                for sym in res['result']:
                    if sym['name'] == "ret_code":
                        logger.info("LARGE ERROR! WHY RET_CODE IN HERE")
                        new_prop = user["traders"][trader]["proportion"]
                        break
                    if sym['name'] in user["traders"][trader]["proportion"]:
                        new_prop[sym['name']] = user["traders"][trader]["proportion"][sym['name']]
                    else:
                        new_prop[sym['name']] = user["traders"][trader]["proportion"][
                            "XRPUSDT"
                        ]
                userdb.update_proportion(user["chat_id"], trader, new_prop)

    def check_noti(self, userdb):
        while not self.stopevent.is_set():
            time.sleep(3)
            allnoti = userdb.get_noti()
            todelete = []
            for noti in allnoti:
                if noti["cmd"] == "delete_and_closeall":
                    chat_id = noti["user"]
                    uid = noti["trader"]
                    user = userdb.get_user(chat_id)
                    if "positions" not in user["traders"][uid]:
                        del user["traders"][uid]
                        userdb.update_user(chat_id, user)
                    else:
                        all_positions = user["traders"][uid]["positions"]
                        # bla bla bla: closing position
                        client = BybitClient(
                            chat_id,
                            user["uname"],
                            user["safety_ratio"],
                            user["api_key"],
                            user["api_secret"],
                            user["slippage"],
                            self,
                            userdb,
                        )
                        txtype, txsymbol, txsize, execprice, isClosedAll = (
                            [],
                            [],
                            [],
                            [],
                            [],
                        )
                        for pos in all_positions:
                            if pos[-4:].upper() == "LONG":
                                txtype.append("CloseLong")
                                txsymbol.append(pos[:-4])
                                txsize.append(float(all_positions[pos]))
                                execprice.append(
                                    float(
                                        client.client.latest_information_for_symbol(
                                            symbol=pos[:-4]
                                        )["result"][0]["mark_price"]
                                    )
                                )
                                isClosedAll.append(True)
                            else:
                                txtype.append("CloseShort")
                                txsymbol.append(pos[:-5])
                                txsize.append(float(all_positions[pos]))
                                execprice.append(
                                    float(
                                        client.client.latest_information_for_symbol(
                                            symbol=pos[:-5]
                                        )["result"][0]["mark_price"]
                                    )
                                )
                                isClosedAll.append(True)
                        txs = pd.DataFrame(
                            {
                                "txtype": txtype,
                                "symbol": txsymbol,
                                "size": txsize,
                                "ExecPrice": execprice,
                                "isClosedAll": isClosedAll,
                            }
                        )
                        prop = user["traders"][uid]["proportion"]
                        for key in prop:
                            prop[key] = 1
                        client.open_trade(
                            txs,
                            uid,
                            prop,
                            user["leverage"],
                            user["traders"][uid]["tmode"],
                            user["traders"][uid]["positions"],
                            user["slippage"],
                            True
                        )
                        del user["traders"][uid]
                        userdb.update_user(chat_id, user)
                        userdb.insert_command(
                            {
                                "cmd": "send_message",
                                "chat_id": chat_id,
                                "message": f"Successfully deleted trader!",
                            }
                        )
                todelete.append(noti["_id"])
            userdb.delete_command(todelete)
