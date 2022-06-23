import threading
import math
import time
import urllib.parse
import sys
from selenium import webdriver
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

sys.path.append("/path/to/binance-copy-trade-bot/data")
sys.path.append("/path/to/binance-copy-trade-bot/config")
from credentials import db_user, db_pw
from config import chrome_location, driver_location
import logging

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
        self.driver_location = driver_location
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
        self.options = options

    def retrieve_command(self, db, stopcond):
        while not stopcond.is_set():
            try:
                msgs = db.getall("commandtable")
                todelete = []
                for msg in msgs:
                    if msg["cmd"] == "send_message":
                        self.updater.bot.sendMessage(msg["chat_id"], msg["message"])
                    todelete.append(msg["_id"])
                db.delete_command(todelete)
            except Exception as e:
                logger.error(f"Connection Error: {str(e)}")
            time.sleep(1)

    def round_up(self, n, decimals=0):
        multiplier = 10**decimals
        return math.ceil(n * multiplier) / multiplier

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

    def get_init_traderPosition(self, trader_url):
        driver = webdriver.Chrome(driver_location, options=self.options)
        driver.get(trader_url)
        WebDriverWait(driver, 4).until(
            EC.presence_of_element_located((By.TAG_NAME, "thead"))
        )
        time.sleep(3)
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, features="html.parser")
        x = soup.get_text()
        ### THIS PART IS ACCORDING TO THE CURRENT WEBPAGE DESIGN WHICH MIGHT BE CHANGED
        x = x.split("\n")[4]
        idx = x.find("Position")
        idx2 = x.find("Start")
        idx3 = x.find("No data")
        x = x[idx:idx2]
        driver.quit()
        if idx3 != -1:
            return "x"
        else:
            output, _ = self.format_results(x, page_source)
            return output["data"]
