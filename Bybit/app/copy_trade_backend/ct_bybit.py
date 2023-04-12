import math
import time
import logging
import pandas as pd
import os
import signal

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
import threading
from pybit.usdt_perpetual import HTTP


class BybitClient:
    def __init__(
        self, chat_id, uname, safety_ratio, api_key, api_secret, slippage, glb, udb
    ):
        self.client = HTTP(
            "https://api.bybit.com",
            api_key=api_key,
            api_secret=api_secret,
            request_timeout=40,
        )  # bybit.bybit(test=False, api_key=api_key, api_secret=api_secret)
        self.api_key = api_key
        self.chat_id = chat_id
        self.uname = uname
        self.stepsize = {}
        self.ticksize = {}
        self.safety_ratio = safety_ratio
        self.isReloaded = False
        res = self.client.query_symbol()
        for symbol in res["result"]:
            # if symbol["name"] not in ["BTCUSDT", "ETHUSDT"]:
            #     continue
            self.ticksize[symbol["name"]] = round(
                -math.log(float(symbol["price_filter"]["tick_size"]), 10)
            )
            self.stepsize[symbol["name"]] = round(
                -math.log(float(symbol["lot_size_filter"]["qty_step"]), 10)
            )
        self.globals = glb
        self.userdb = udb

    def get_latest_price(self, symbol):
        return self.globals.calculated_price[symbol]

    def get_symbols(self):
        symbolList = []
        for symbol in self.stepsize:
            symbolList.append(symbol)
        return symbolList

    def tpsl_trade(
        self, symbol, side, qty, excprice, leverage, tp, sl, skey
    ):  # make sure everything in numbers not text//side: original side
        logger.info(f"Debug Check {leverage}/{tp}/{sl}")
        if side == "Buy":
            if tp != -1:
                tpPrice1 = excprice * (1 + (tp / leverage) / 100)
                qty1 = "{:0.0{}f}".format(qty, self.stepsize[symbol])
                tpPrice1 = "{:0.0{}f}".format(tpPrice1, self.ticksize[symbol])
                try:
                    result = self.client.set_trading_stop(
                        symbol=symbol,
                        take_profit=float(tpPrice1),
                        tp_trigger_by="MarkPrice",
                        tp_size=float(qty1),
                    )
                    if result["ret_msg"] != "OK":
                        logger.error(f"Error in tpsl: {result['ret_msg']}")
                except:
                    logger.error("some error again")
            if sl != -1:
                tpPrice2 = excprice * (1 - (sl / leverage) / 100)
                qty2 = "{:0.0{}f}".format(qty, self.stepsize[symbol])
                tpPrice2 = "{:0.0{}f}".format(tpPrice2, self.ticksize[symbol])
                try:
                    result = self.client.set_trading_stop(
                        symbol=symbol,
                        stop_loss=float(tpPrice2),
                        sl_trigger_by="MarkPrice",
                        sl_size=float(qty2),
                    )
                    if result["ret_msg"] != "OK":
                        logger.error(f"Error in tpsl: {result['ret_msg']}")
                except:
                    logger.error("SL error")
        else:
            if tp != -1:
                tpPrice1 = excprice * (1 - (tp / leverage) / 100)
                qty1 = "{:0.0{}f}".format(qty, self.stepsize[symbol])
                tpPrice1 = "{:0.0{}f}".format(tpPrice1, self.ticksize[symbol])
                try:
                    result = self.client.set_trading_stop(
                        symbol=symbol,
                        take_profit=float(tpPrice1),
                        tp_trigger_by="MarkPrice",
                        tp_size=float(qty1),
                    )
                    if result["ret_msg"] != "OK":
                        logger.error(f"Error in tpsl: {result['ret_msg']}")
                except:
                    logger.error("some error again")
            if sl != -1:
                tpPrice2 = excprice * (1 + (sl / leverage) / 100)
                qty2 = "{:0.0{}f}".format(qty, self.stepsize[symbol])
                tpPrice2 = "{:0.0{}f}".format(tpPrice2, self.ticksize[symbol])
                try:
                    result = self.client.set_trading_stop(
                        symbol=symbol,
                        stop_loss=float(tpPrice2),
                        sl_trigger_by="MarkPrice",
                        sl_size=float(qty2),
                    )
                    if result["ret_msg"] != "OK":
                        logger.error(f"Error in tpsl: {result['ret_msg']}")
                except:
                    logger.error("SL error")
        return

    def query_trade(
        self,
        orderId,
        symbol,
        positionKey,
        isOpen,
        uname,
        takeProfit,
        stopLoss,
        Leverage,
        positionSide,
        ref_price,
        uid,
        todelete
    ):  # ONLY to be run as thread
        numTries = 0
        time.sleep(1)
        result = ""
        executed_qty = 0
        while True:
            try:
                result = self.client.query_active_order(symbol=symbol, order_id=orderId)
                if result["ret_msg"] != "OK":
                    logger.error("There is an error!")
                    return
                result = result["result"]
                if result["order_status"] == "Filled":
                    if ref_price != -1:
                        executed_price = float(result["last_exec_price"])
                        diff = abs(executed_price - ref_price)
                        slippage = diff / ref_price * 100
                        self.userdb.insert_command(
                            {
                                "cmd": "send_message",
                                "chat_id": self.chat_id,
                                "message": f"Order ID {orderId} ({positionKey}) fulfilled successfully. The slippage is {slippage:.2f}%.",
                            }
                        )
                    else:
                        self.userdb.insert_command(
                            {
                                "cmd": "send_message",
                                "chat_id": self.chat_id,
                                "message": f"Order ID {orderId} ({positionKey}) fulfilled successfully.",
                            }
                        )
                    if todelete:
                        return
                    resultqty = round(abs(float(result["cum_exec_qty"])), 3)
                    resultqty = -resultqty if positionSide == "SHORT" else resultqty
                    # ADD TO POSITION
                    if isOpen:
                        resultqty = round(abs(float(result["cum_exec_qty"])), 3)
                        resultqty = -resultqty if positionSide == "SHORT" else resultqty
                        self.userdb.update_positions(
                            self.chat_id, uid, positionKey, resultqty, 1
                        )
                        try:
                            self.tpsl_trade(
                                symbol,
                                result["side"],
                                float(result["cum_exec_qty"]),
                                float(result["last_exec_price"]),
                                Leverage,
                                takeProfit,
                                stopLoss,
                                positionKey,
                            )
                        except:
                            pass
                    else:
                        resultqty = round(abs(float(result["cum_exec_qty"])), 3)
                        resultqty = -resultqty if positionSide == "SHORT" else resultqty
                        self.userdb.update_positions(
                            self.chat_id, uid, positionKey, resultqty, 2
                        )
                        # check positions thenn close all
                        # res = self.client.my_position(symbol=symbol)
                        # checkside = "Buy" if result["side"] == "Sell" else "Sell"
                        # for pos in res["result"]:
                        #     if pos["side"] == checkside and float(pos["size"]) == 0:
                        #         self.userdb.update_positions(
                        #             self.chat_id, subacc, positionKey, 0, 0
                        #         )
                    return
                elif result["order_status"] in [
                    "Rejected",
                    "PendingCancel",
                    "Cancelled",
                ]:
                    self.userdb.insert_command(
                        {
                            "cmd": "send_message",
                            "chat_id": self.chat_id,
                            "message": f"Order ID {orderId} ({positionKey}) is cancelled/rejected.",
                        }
                    )
                    return
                elif result["order_status"] == "PartiallyFilled":
                    updatedQty = float(result["cum_exec_qty"]) - executed_qty
                    updatedQty = -updatedQty if positionSide == "SHORT" else updatedQty
                    if todelete:
                        continue
                    if isOpen:
                        self.userdb.update_positions(
                            self.chat_id, uid, positionKey, resultqty, 1
                        )
                    else:
                        self.userdb.update_positions(
                            self.chat_id, uid, positionKey, resultqty, 2
                        )
                    executed_qty = float(result["cum_exec_qty"])
            except Exception as e:
                logger.error("eeerrroooorrr")
                logger.error(str(e))
                pass
            if numTries >= 15:
                break
            time.sleep(60)
            numTries += 1
        if result != "" and result["order_status"] == "PartiallyFilled":
            self.userdb.insert_command(
                {
                    "cmd": "send_message",
                    "chat_id": self.chat_id,
                    "message": f"Order ID {orderId} ({positionKey}) is only partially filled. The rest will be cancelled.",
                }
            )
            try:
                self.client.cancel_active_order(symbol=symbol, order_id=orderId)
                self.tpsl_trade(
                    symbol,
                    result["side"],
                    float(result["cum_exec_qty"]),
                    float(result["last_exec_price"]),
                    Leverage,
                    takeProfit,
                    stopLoss,
                    positionKey,
                )
            except:
                pass

        if result != "" and result["order_status"] == "New":
            self.userdb.insert_command(
                {
                    "cmd": "send_message",
                    "chat_id": self.chat_id,
                    "message": f"Order ID {orderId} ({positionKey}) has not been filled. It will be cancelled.",
                }
            )
            try:
                self.client.cancel_active_order(symbol=symbol, order_id=orderId)
            except:
                pass

    def open_trade(
        self,
        df,
        uid,
        proportion,
        leverage,
        tmodes,
        positions,
        slippage,
        todelete = False
    ):
        # logger.info("DEBUGx\n" + df.to_string())
        df = df.values
        i = -1
        for tradeinfo in df:
            i += 1
            isOpen = False
            types = tradeinfo[0].upper()
            balance, collateral, coin = 0, 0, ""
            if not tradeinfo[1] in proportion:
                self.userdb.insert_command(
                    {
                        "cmd": "send_message",
                        "chat_id": self.chat_id,
                        "message": f"This trade will not be executed since {tradeinfo[1]} is not a valid symbol.",
                    }
                )
                continue
            try:
                coin = "USDT"
                res = self.client.get_wallet_balance(coin=coin)["result"]["USDT"]
                balance = res["available_balance"]
            except:
                coin = "USDT"
                balance = "0"
                logger.error("Cannot retrieve balance.")
            balance = float(balance)
            if types[:4] == "OPEN":
                isOpen = True
                positionSide = types[4:]
                if positionSide == "LONG":
                    side = "Buy"
                else:
                    side = "Sell"
                try:
                    self.client.set_leverage(
                        symbol=tradeinfo[1], buy_leverage=leverage[tradeinfo[1]],sell_leverage=leverage[tradeinfo[1]]
                    )
                except Exception as e:
                    logger.error(f"Leverage error {str(e)}")
                    pass
            else:
                positionSide = types[5:]
                if positionSide == "LONG":
                    side = "Sell"
                else:
                    side = "Buy"
            checkKey = tradeinfo[1] + positionSide
            quant = abs(float(tradeinfo[2])) * proportion[tradeinfo[1]]
            if not isOpen and (
                (checkKey not in positions) or (positions[checkKey] == 0)
            ):
                self.userdb.insert_command(
                    {
                        "cmd": "send_message",
                        "chat_id": self.chat_id,
                        "message": f"Close {checkKey}: This trade will not be executed because your opened positions with this strategy is 0.",
                    }
                )
                continue
            if quant == 0:
                self.userdb.insert_command(
                    {
                        "cmd": "send_message",
                        "chat_id": self.chat_id,
                        "message": f"{side} {checkKey}: This trade will not be executed because size = 0. Adjust proportion if you want to follow.",
                    }
                )
                continue
            latest_price = float(
                self.client.latest_information_for_symbol(symbol=tradeinfo[1])[
                    "result"
                ][0]["mark_price"]
            )
            if isinstance(tradeinfo[3],str):
                exec_price = float(tradeinfo[3].replace(",",""))
            else:
                exec_price = float(tradeinfo[3])
            if abs(latest_price - exec_price) / exec_price > slippage and isOpen:
                self.userdb.insert_command(
                    {
                        "cmd": "send_message",
                        "chat_id": self.chat_id,
                        "message": f"The execute price of {tradeinfo[1]} is {exec_price}, but the current price is {latest_price}, which is over the preset slippage of {slippage}. The trade will not be executed.",
                    }
                )
                continue
            reqticksize = self.ticksize[tradeinfo[1]]
            reqstepsize = self.stepsize[tradeinfo[1]]
            if not isOpen and tradeinfo[4]:
                if abs(positions[checkKey]) > abs(quant):
                    quant = abs(positions[checkKey])
            collateral = (latest_price * quant) / leverage[tradeinfo[1]]
            quant = self.round_up(quant, reqstepsize)
            quant = str(quant)
            if isOpen:
                self.userdb.insert_command(
                    {
                        "cmd": "send_message",
                        "chat_id": self.chat_id,
                        "message": f"For the following trade, you will need {collateral:.3f}{coin} as collateral.",
                    }
                )
                if collateral >= balance * self.safety_ratio:
                    self.userdb.insert_command(
                        {
                            "cmd": "send_message",
                            "chat_id": self.chat_id,
                            "message": f"WARNING: this trade will take up more than {self.safety_ratio} of your available balance. It will NOT be executed. Manage your risks accordingly and reduce proportion if necessary.",
                        }
                    )
                    continue
            if tmodes[tradeinfo[1]] == 0 or (tmodes[tradeinfo[1]] == 2 and not isOpen):
                try:
                    tosend = f"Trying to execute the following trade:\nSymbol: {tradeinfo[1]}\nSide: {side}\npositionSide: {positionSide}\ntype: MARKET\nquantity: {quant}"
                    self.userdb.insert_command(
                        {
                            "cmd": "send_message",
                            "chat_id": self.chat_id,
                            "message": tosend,
                        }
                    )
                    if isOpen:
                        response = self.client.place_active_order(
                            side=side,
                            symbol=tradeinfo[1],
                            order_type="Market",
                            qty=quant,
                            time_in_force="GoodTillCancel",
                            reduce_only=False,
                            close_on_trigger=False,
                        )
                    else:
                        response = self.client.place_active_order(
                            side=side,
                            symbol=tradeinfo[1],
                            order_type="Market",
                            qty=quant,
                            time_in_force="GoodTillCancel",
                            reduce_only=True,
                            close_on_trigger=True,
                        )
                    if response["ret_msg"] == "OK":
                        logger.info(f"{self.uname} opened order.")
                    else:
                        logger.error(f"Error: {response['ret_msg']}")
                        self.userdb.insert_command(
                            {
                                "cmd": "send_message",
                                "chat_id": self.chat_id,
                                "message": f"Error: {response['ret_msg']}",
                            }
                        )
                        retmsg = response["ret_msg"]
                        if retmsg.find("reduce-only") != -1:
                            self.userdb.update_positions(
                                self.chat_id, uid, checkKey, 0, 0
                            )
                        continue
                    t1 = threading.Thread(
                        target=self.query_trade,
                        args=(
                            response["result"]["order_id"],
                            tradeinfo[1],
                            checkKey,
                            isOpen,
                            self.uname,
                            -1,
                            -1,
                            leverage[tradeinfo[1]],
                            positionSide,
                            -1,
                            uid,
                            todelete
                        ),
                    )
                    t1.start()
                except Exception as e:
                    logger.error(str(e))
                    if str(e).find("reduce-only") != -1:
                        self.userdb.update_positions(
                                self.chat_id, uid, checkKey, 0, 0
                            )
                        self.userdb.insert_command(
                            {
                                "cmd": "send_message",
                                "chat_id": self.chat_id,
                                "message": "Your opened position is 0, no positions has been closed.",
                            }
                        )
                    logger.error("Error in processing request during trade opening.")
            else:
                if isinstance(tradeinfo[3], str):
                    tradeinfo[3] = tradeinfo[3].replace(",", "")
                target_price = float(tradeinfo[3])
                target_price = "{:0.0{}f}".format(target_price, reqticksize)
                try:
                    tosend = f"Trying to execute the following trade:\nSymbol: {tradeinfo[1]}\nSide: {side}\ntype: LIMIT\nquantity: {quant}\nPrice: {target_price}"
                    self.userdb.insert_command(
                        {
                            "cmd": "send_message",
                            "chat_id": self.chat_id,
                            "message": tosend,
                        }
                    )
                    if isOpen:
                        response = self.client.place_active_order(
                            side=side,
                            symbol=tradeinfo[1],
                            order_type="Limit",
                            qty=quant,
                            price=target_price,
                            time_in_force="GoodTillCancel",
                            reduce_only=False,
                            close_on_trigger=False,
                        )
                    else:
                        response = self.client.place_active_order(
                            side=side,
                            symbol=tradeinfo[1],
                            order_type="Limit",
                            qty=quant,
                            price=target_price,
                            time_in_force="GoodTillCancel",
                            reduce_only=True,
                            close_on_trigger=True,
                        )
                    if response["ret_msg"] == "OK":
                        logger.info(f"{self.uname} opened order.")
                    else:
                        logger.error(f"Error: {response['ret_msg']}")
                        continue
                    t1 = threading.Thread(
                        target=self.query_trade,
                        args=(
                            response["result"]["order_id"],
                            tradeinfo[1],
                            checkKey,
                            isOpen,
                            self.uname,
                            -1,
                            -1,
                            leverage[tradeinfo[1]],
                            positionSide,
                            -1,
                            uid,
                            todelete
                        ),
                    )
                    t1.start()
                except Exception as e:
                    logger.error("have error!!")
                    logger.info(str(e))

    def get_positions(self):
        try:
            result2 = self.client.my_position()["result"]
        except Exception as e:
            if str(e).find("Invalid") != -1:
                logger.error(str(e))
                return -1
            for line in os.popen("ps ax | grep tg_"):
                fields = line.split()
                pid = fields[0]
                try:
                    os.kill(int(pid), signal.SIGKILL)
                except:
                    pass
            exit(-1)
        symbol = []
        size = []
        EnPrice = []
        MarkPrice = []
        PNL = []
        margin = []
        if result2 is None:
            return -1
        # if self.time_in_danger():
        #     logger.info("Skipping checking during unstable time.")
        #     continue
        for pos in result2:
            try:
                pos = pos["data"]
            except:
                logger.error("Error! but no worries.")
                break
            if float(pos["size"]) != 0:
                symbol.append(pos["symbol"])
                tsize = pos["size"]
                tsize = tsize if pos["side"] == "Buy" else -tsize
                size.append(tsize)
                EnPrice.append(pos["entry_price"])
                try:
                    mp = self.get_latest_price(pos["symbol"])
                except:
                    mp = 0
                MarkPrice.append(mp)
                PNL.append(pos["unrealised_pnl"])
                margin.append(pos["leverage"])
        return pd.DataFrame(
            {
                "symbol": symbol,
                "size": size,
                "Entry Price": EnPrice,
                "Mark Price": MarkPrice,
                "PNL": PNL,
                "leverage": margin,
            }
        )

    def round_up(self, n, decimals=0):
        multiplier = 10**decimals
        return math.ceil(n * multiplier) / multiplier
