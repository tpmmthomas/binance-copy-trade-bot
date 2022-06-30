import threading
from ct_bybit import BybitClient
import sys

sys.path.append("/home/thomas/binance-copy-trade-bot/config")
from config import chrome_location, driver_location
import time
import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
import pandas as pd
from selenium import webdriver
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

options = webdriver.ChromeOptions()
options.binary_location = chrome_location
options.add_argument("--headless")
options.add_argument("--disable-web-security")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--allow-running-insecure-content")
options.add_argument("--disable-extensions")
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument("--disable-dev-shm-usage")


class WebScraping(threading.Thread):
    def __init__(self, globals, userdb):
        threading.Thread.__init__(self)
        self.driver = webdriver.Chrome(driver_location, options=options)
        self.i = 0
        self.isStop = threading.Event()
        self.pauseload = threading.Event()
        self.cond = {}
        self.userdb = userdb
        self.globals = globals
        self.changeNotiTime = {}
        self.num_no_data = {}
        self.error = {}
        # self.thislock = threading.Lock()

    @staticmethod
    def format_results(x, y):
        words = []
        prev_idx = 0
        i = 0
        while i < len(x):
            result = y.find(x[prev_idx:i])
            if result == -1:
                while i >= 0 and y.find(x[prev_idx : i - 1] + "<") == -1:
                    i -= 1
                words.append(x[prev_idx : i - 1])
                prev_idx = i - 1
            i += 1
        words.append(x[prev_idx:])
        times = words[0]
        words = words[6:]
        symbol = words[::5]
        size = words[1::5]
        entry_price = words[2::5]
        mark_price = words[3::5]
        pnl = words[4::5]
        margin = []
        calculatedMargin = []
        for i in range(len(mark_price)):
            idx1 = pnl[i].find("(")
            idx2 = pnl[i].find("%")
            percentage = float(pnl[i][idx1 + 1 : idx2].replace(",", "")) / 100
            if float(entry_price[i].replace(",", "")) == 0:
                margin.append("nan")
                calculatedMargin.append(False)
                continue
            price = (
                float(mark_price[i].replace(",", ""))
                - float(entry_price[i].replace(",", ""))
            ) / float(entry_price[i].replace(",", ""))
            if percentage == 0 or price == 0:
                margin.append("nan")
                calculatedMargin.append(False)
            else:
                estimated_margin = abs(round(percentage / price))
                calculatedMargin.append(True)
                margin.append(str(estimated_margin) + "x")
        dictx = {
            "symbol": symbol,
            "size": size,
            "Entry Price": entry_price,
            "Mark Price": mark_price,
            "PNL (ROE%)": pnl,
            "Estimated Margin": margin,
        }
        df = pd.DataFrame(dictx)
        return {"time": times, "data": df}, calculatedMargin

    def changes(self, df, df2):
        txtype = []
        txsymbol = []
        txsize = []
        executePrice = []
        isClosedAll = []
        if (isinstance(df, str) or df is None) and (
            isinstance(df2, str) or df2 is None
        ):
            return None
        if isinstance(df, str):
            for index, row in df2.iterrows():
                size = row["size"]
                if isinstance(size, str):
                    size = size.replace(",", "")
                size = float(size)
                if size > 0:
                    txtype.append("OpenLong")
                    txsymbol.append(row["symbol"])
                    txsize.append(size)
                    executePrice.append(row["Entry Price"])
                    isClosedAll.append(False)
                else:
                    txtype.append("OpenShort")
                    txsymbol.append(row["symbol"])
                    txsize.append(size)
                    executePrice.append(row["Entry Price"])
                    isClosedAll.append(False)
            txs = pd.DataFrame(
                {
                    "txtype": txtype,
                    "symbol": txsymbol,
                    "size": txsize,
                    "ExecPrice": executePrice,
                    "isClosedAll": isClosedAll,
                }
            )
        elif isinstance(df2, str):
            for index, row in df.iterrows():
                size = row["size"]
                if isinstance(size, str):
                    size = size.replace(",", "")
                size = float(size)
                if size > 0:
                    txtype.append("CloseLong")
                    txsymbol.append(row["symbol"])
                    txsize.append(-size)
                    executePrice.append(row["Mark Price"])
                    isClosedAll.append(True)
                else:
                    txtype.append("CloseShort")
                    txsymbol.append(row["symbol"])
                    txsize.append(-size)
                    executePrice.append(row["Mark Price"])
                    isClosedAll.append(True)
            txs = pd.DataFrame(
                {
                    "txtype": txtype,
                    "symbol": txsymbol,
                    "size": txsize,
                    "ExecPrice": executePrice,
                    "isClosedAll": isClosedAll,
                }
            )
        else:
            df, df2 = df.copy(), df2.copy()
            for index, row in df.iterrows():
                hasChanged = False
                temp = df2["symbol"] == row["symbol"]
                idx = df2.index[temp]
                size = row["size"]
                if isinstance(size, str):
                    size = size.replace(",", "")
                size = float(size)
                oldentry = row["Entry Price"]
                if isinstance(oldentry, str):
                    oldentry = oldentry.replace(",", "")
                oldentry = float(oldentry)
                oldmark = row["Mark Price"]
                if isinstance(oldmark, str):
                    oldmark = oldmark.replace(",", "")
                oldmark = float(oldmark)
                isPositive = size >= 0
                for r in idx:
                    df2row = df2.loc[r].values
                    newsize = df2row[1]
                    if isinstance(newsize, str):
                        newsize = newsize.replace(",", "")
                    newsize = float(newsize)
                    newentry = df2row[2]
                    if isinstance(newentry, str):
                        newentry = newentry.replace(",", "")
                    newentry = float(newentry)
                    newmark = df2row[3]
                    if isinstance(newmark, str):
                        newmark = newmark.replace(",", "")
                    newmark = float(newmark)
                    if newsize == size:
                        df2 = df2.drop(r)
                        hasChanged = True
                        break
                    if isPositive and newsize > 0:
                        changesize = newsize - size
                        if changesize > 0:
                            txtype.append("OpenLong")
                            txsymbol.append(df2row[0])
                            txsize.append(changesize)
                            isClosedAll.append(False)
                            try:
                                exp = (
                                    newentry * newsize - oldentry * size
                                ) / changesize
                            except:
                                exp = 0
                            if changesize / newsize < 0.05:
                                executePrice.append(newmark)
                            else:
                                executePrice.append(exp)
                        else:
                            txtype.append("CloseLong")
                            txsymbol.append(df2row[0])
                            txsize.append(changesize)
                            executePrice.append(newmark)
                            isClosedAll.append(False)
                        df2 = df2.drop(r)
                        hasChanged = True
                        break
                    if not isPositive and newsize < 0:
                        changesize = newsize - size
                        if changesize > 0:
                            txtype.append("CloseShort")
                            txsymbol.append(df2row[0])
                            txsize.append(changesize)
                            executePrice.append(newmark)
                            isClosedAll.append(False)
                        else:
                            txtype.append("OpenShort")
                            txsymbol.append(df2row[0])
                            txsize.append(changesize)
                            isClosedAll.append(False)
                            try:
                                exp = (
                                    newentry * newsize - oldentry * size
                                ) / changesize
                            except:
                                exp = 0
                            if changesize / newsize < 0.05:
                                executePrice.append(newmark)
                            else:
                                executePrice.append(exp)
                        df2 = df2.drop(r)
                        hasChanged = True
                        break
                if not hasChanged:
                    if size > 0:
                        txtype.append("CloseLong")
                        txsymbol.append(row["symbol"])
                        txsize.append(-size)
                        executePrice.append(oldmark)
                        isClosedAll.append(True)
                    else:
                        txtype.append("CloseShort")
                        txsymbol.append(row["symbol"])
                        txsize.append(-size)
                        executePrice.append(oldmark)
                        isClosedAll.append(True)
            for index, row in df2.iterrows():
                size = row["size"]
                if isinstance(size, str):
                    size = size.replace(",", "")
                size = float(size)
                if size > 0:
                    txtype.append("OpenLong")
                    txsymbol.append(row["symbol"])
                    txsize.append(size)
                    executePrice.append(row["Entry Price"])
                    isClosedAll.append(False)
                else:
                    txtype.append("OpenShort")
                    txsymbol.append(row["symbol"])
                    txsize.append(size)
                    executePrice.append(row["Entry Price"])
                    isClosedAll.append(False)
            txs = pd.DataFrame(
                {
                    "txType": txtype,
                    "symbol": txsymbol,
                    "size": txsize,
                    "ExecPrice": executePrice,
                    "isClosedAll": isClosedAll,
                }
            )
        return txs  # add this to open trade part

    def position_changes(self, source, uid, prev_df, name, lasttime):
        soup = BeautifulSoup(source, features="html.parser")
        x = soup.get_text()
        ### THIS PART IS ACCORDING TO THE CURRENT WEBPAGE DESIGN WHICH MIGHT BE CHANGED
        x = x.split("\n")[4]
        idx = x.find("Position")
        idx2 = x.find("Start")
        idx3 = x.find("No data")
        x = x[idx:idx2]
        following_users = self.userdb.fetch_following(uid)
        try:
            prev_position = self.userdb.fetch_trader_position(uid)
        except:
            logger.info(f"{uid} Cannot get past positions.")
            return
        if uid not in self.error:
            self.error[uid] = 0
        elif self.error[uid] > 20:
            self.error[uid] = 0
            # tosend = f"Trader {name} might not be sharing positions anymore."
            # for users in following_users:
            #     self.userdb.insert_command(
            #         {
            #             "cmd": "send_message",
            #             "chat_id": users["chat_id"],
            #             "message": tosend,
            #         }
            #     )
        if idx3 != -1:
            self.error[uid] = 0
            self.num_no_data[uid] = (
                1 if uid not in self.num_no_data else self.num_no_data[uid] + 1
            )
            if self.num_no_data[uid] > 35:
                self.num_no_data[uid] = 4
            if self.num_no_data[uid] >= 3 and prev_position != "x":
                logger.info(f"{name} Change to no position.")
                self.userdb.save_position(uid, "x",True)
                # self.changeNotiTime[uid] = datetime.now()
                now = datetime.now() + timedelta(hours=8)
                # self.lastPosTime = datetime.now() + timedelta(hours=8)
                tosend = (
                    f"Trader {name}, Current time: " + str(now) + "\nNo positions.\n"
                )
                txlist = self.changes(prev_df, "x")
                for users in following_users:
                    self.userdb.insert_command(
                        {
                            "cmd": "send_message",
                            "chat_id": users["chat_id"],
                            "message": tosend,
                        }
                    )
                    if users['traders'][uid]["toTrade"]:
                        tosend = "Making the following trades: \n" + txlist.to_string()
                        self.userdb.insert_command(
                            {
                                "cmd": "send_message",
                                "chat_id": users["chat_id"],
                                "message": tosend,
                            }
                        )
                        client = BybitClient(
                            users["chat_id"],
                            users["uname"],
                            users["safety_ratio"],
                            users["api_key"],
                            users["api_secret"],
                            users["slippage"],
                            self.globals,
                            self.userdb,
                        )
                        client.open_trade(
                            txlist,
                            uid,
                            users["traders"][uid]["proportion"],
                            users["leverage"],
                            users["traders"][uid]["tmode"],
                            users["traders"][uid]["positions"],
                            users["slippage"],
                        )
                        del client
            elif self.num_no_data[uid] >= 3:
                self.userdb.save_position(uid, "x",False)
            diff = datetime.now() - datetime.strptime(lasttime, "%y-%m-%d %H:%M:%S")
            # if diff.total_seconds() / 3600 >= 24:
                # for users in following_users:
                #     self.userdb.insert_command(
                #         {
                #             "cmd": "send_message",
                #             "chat_id": users["chat_id"],
                #             "message": f"Trader {name}: 24 hours no position update.",
                #         }
                #     )
        else:
            self.num_no_data[uid] = 0
            try:
                output, calmargin = self.format_results(x, source)
            except Exception as e:
                self.error[uid] += 1
                logger.error(f"Trader {name} may not share position anymore.")
                return
            if output["data"].empty:
                self.error[uid] += 1
                return
            if prev_position == "x":
                isChanged = True
                txlist = self.changes(prev_position, output["data"])
            else:
                prev_position = pd.read_json(prev_position)
                try:
                    toComp = output["data"][["symbol", "size", "Entry Price"]]
                    prevdf = prev_position[["symbol", "size", "Entry Price"]]
                except:
                    self.error[uid] += 1
                if not toComp.equals(prevdf):
                    txlist = self.changes(prev_position, output["data"])
                    if not txlist.empty:
                        isChanged = True
                    else:
                        isChanged = False
                else:
                    isChanged = False
            if isChanged:
                self.userdb.save_position(uid, output["data"].to_json(),True)
                logger.info(f"{name} changed positions.")
                now = datetime.now() + timedelta(hours=8)
                self.lastPosTime = datetime.now() + timedelta(hours=8)
                numrows = output["data"].shape[0]
                if numrows <= 10:
                    tosend = (
                        f"Trader {name}, Current time: "
                        + str(now)
                        + "\n"
                        + output["time"]
                        + "\n"
                        + output["data"].to_string()
                        + "\n"
                    )
                    for users in following_users:
                        self.userdb.insert_command(
                            {
                                "cmd": "send_message",
                                "chat_id": users["chat_id"],
                                "message": tosend,
                            }
                        )
                else:
                    firstdf = output["data"].iloc[0:10]
                    tosend = (
                        f"Trader {name}, Current time: "
                        + str(now)
                        + "\n"
                        + output["time"]
                        + "\n"
                        + firstdf.to_string()
                        + "\n(cont...)"
                    )
                    for users in following_users:
                        self.userdb.insert_command(
                            {
                                "cmd": "send_message",
                                "chat_id": users["chat_id"],
                                "message": tosend,
                            }
                        )
                    for i in range(numrows // 10):
                        seconddf = output["data"].iloc[
                            (i + 1) * 10 : min(numrows, (i + 2) * 10)
                        ]
                        if not seconddf.empty:
                            for users in following_users:
                                self.userdb.insert_command(
                                    {
                                        "cmd": "send_message",
                                        "chat_id": users["chat_id"],
                                        "message": seconddf.to_string(),
                                    }
                                )
                # txlist = self.changes(prev_position, output["data"])
                for users in following_users:
                    if users["traders"][uid]["toTrade"] and not txlist.empty:
                        tosend = "Making the following trades: \n" + txlist.to_string()
                        self.userdb.insert_command(
                            {
                                "cmd": "send_message",
                                "chat_id": users["chat_id"],
                                "message": tosend,
                            }
                        )
                        client = BybitClient(
                            users["chat_id"],
                            users["uname"],
                            users["safety_ratio"],
                            users["api_key"],
                            users["api_secret"],
                            users["slippage"],
                            self.globals,
                            self.userdb,
                        )
                        client.open_trade(
                            txlist,
                            uid,
                            users["traders"][uid]["proportion"],
                            users["leverage"],
                            users["traders"][uid]["tmode"],
                            users["traders"][uid]["positions"],
                            users["slippage"],
                        )
                        del client
            else:
                self.userdb.save_position(uid, output["data"].to_json(),False)
        self.first_run = False
        self.error[uid] = 0
        diff = datetime.now() - datetime.strptime(lasttime, "%y-%m-%d %H:%M:%S")
        # if diff.total_seconds() / 3600 >= 24:
        #     for users in following_users:
        #         self.userdb.insert_command(
        #             {
        #                 "cmd": "send_message",
        #                 "chat_id": users["chat_id"],
        #                 "message": f"Trader {self.name}: 24 hours no position update.",
        #             }
        #         )

    def run(self):  # get the positions
        while not self.isStop.is_set():
            if self.pauseload.is_set():
                time.sleep(5)
                continue
            # try:
            urls = self.userdb.retrieve_traders()
            for uid in urls:
                # logger.info(f"Running {uid['name']}.")
                try:
                    self.driver.get(uid["url"])
                except:
                    logger.error("cannot fetch url")
                    continue
                try:
                    WebDriverWait(self.driver, 4).until(
                        EC.presence_of_element_located((By.TAG_NAME, "thead"))
                    )
                except:
                    logger.error(f"{uid['name']} cannot get webpage.")
                    continue
                time.sleep(3)
                page_source = self.driver.page_source
                if uid["positions"] != "x":
                    prevpos = pd.read_json(uid["positions"])
                else:
                    prevpos = "x"
                self.position_changes(
                    page_source, uid["uid"], prevpos, uid["name"], uid["lastPosTime"]
                )
            self.i += 1
            if self.i >= 60:
                self.driver.quit()
                self.driver = None
                time.sleep(6)
                self.driver = webdriver.Chrome(driver_location, options=options)
                self.i = 0
            # except Exception as e:
            #     logger.error(str(e))
            #     logger.error("Oh no uncaught problem")
            #     self.driver.quit()
            #     self.driver = None
            #     time.sleep(6)
            #     self.driver = webdriver.Chrome(driver_location, options=options)
            time.sleep(1)

    def stop(self):
        self.isStop.set()

    def pause(self):
        self.pauseload.set()

    def resume(self):
        self.pauseload.clear()
