import threading
import math
import time
import urllib.parse
import sys
# from selenium import webdriver
import pandas as pd
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from bs4 import BeautifulSoup
import requests
import re
from app.data.credentials import db_user, db_pw
from app.config.config import chrome_location, driver_location
import logging
from datetime import datetime

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class tgGlobals:
    # Define integer flags for use in Event Handlers
    def __init__(self, udt):
        username = urllib.parse.quote_plus(db_user)
        password = urllib.parse.quote_plus(db_pw)
        self.dbpath = "mongodb://%s:%s@localhost:27017/" % (username, password)
        self.is_reloading = False
        self.reloading = False
        self.updater = udt  # Updater(cnt.bot_token2)
        self.dictLock = threading.Lock()
        self.piclock = threading.Lock()
        self.stop_update = False
        self.current_position = None
        self.current_balance = None
        # self.driver_location = driver_location
        # options = webdriver.ChromeOptions()
        # options.binary_location = chrome_location
        # options.add_argument("--headless")
        # options.add_argument("--disable-web-security")
        # options.add_argument("--ignore-certificate-errors")
        # options.add_argument("--allow-running-insecure-content")
        # options.add_argument("--disable-extensions")
        # options.add_argument("--no-sandbox")
        # options.add_argument("--disable-gpu")
        # options.add_argument("--disable-dev-shm-usage")
        # self.options = options

    def retrieve_command(self, db, stopcond):
        while not stopcond.is_set():
            time.sleep(1)
            msgs = db.getall("commandtable")
            for msg in msgs:
                todelete = []
                if msg["cmd"] == "send_message":
                    try:
                        for i in range(len(msg['message'])//500 + 1):
                            time.sleep(0.1)
                            sendmsg = msg["message"][500*i:500*(i+1)]
                            if re.sub(r'[^a-zA-Z0-9]+','', sendmsg) != "":
                                self.updater.bot.sendMessage(msg["chat_id"], sendmsg)
                        todelete.append(msg["_id"])
                        db.delete_command(todelete)
                    except Exception as e:
                        logger.error(f"Connection Error: {str(e)}")
    def round_up(self, n, decimals=0):
        multiplier = 10**decimals
        return math.ceil(n * multiplier) / multiplier

    @staticmethod
    def format_results(poslist,times):
        symbol = []
        size = []
        entry_price = []
        mark_price = []
        pnl = []
        margin = []
        calculatedMargin = []
        times =  datetime.utcfromtimestamp(times/1000).strftime('%Y-%m-%d %H:%M:%S')
        for dt in poslist:
            symbol.append(dt['symbol'])
            size.append(dt['amount'])
            entry_price.append(dt['entryPrice'])
            mark_price.append(dt['markPrice'])
            pnl.append(f"{round(dt['pnl'],2)} ({round(dt['roe']*100,2)}%)")
            percentage = dt['roe']
            if float(dt['entryPrice']) == 0:
                margin.append("nan")
                calculatedMargin.append(False)
                continue
            price = (
                float(dt['markPrice'])
                - float(dt['entryPrice'])
            ) / float(dt['entryPrice'])
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

    def get_init_traderPosition(self, uid):
        try:
            r = requests.post("https://www.binance.com/bapi/futures/v1/public/future/leaderboard/getOtherPosition",json={
                "encryptedUid": uid,
                "tradeType": "PERPETUAL"
            })
            assert r.status_code == 200
            positions = r.json()['data']['otherPositionRetList']
            times = r.json()['data']['updateTimeStamp']
            assert positions is not None
            assert times is not None
        except Exception as e:
            logger.error(str(e))
            return "x"
        output, _ = self.format_results(positions,times)
        return output["data"]
