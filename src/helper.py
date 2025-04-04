from traceback import print_exc
import re
from stock_brokers.finvasia.finvasia import Finvasia
from stock_brokers.finvasia.api_helper import (
    post_order_hook,
)
from constants import O_CNFG, logging, O_SETG
import pendulum as pdlm
from toolkit.kokoo import blink, timer
from wserver import Wserver
from paper import Paper


def find_underlying(symbol):
    try:
        for underlying, low in O_SETG["MCX"].items():
            # starts with any alpha
            pattern = re.compile(r"[A-Za-z]+")
            symbol_begin = pattern.match(symbol).group()
            underlying_begin = pattern.match(underlying).group()
            # If the symbol begins with the alpha of underlying
            if symbol_begin.startswith(underlying_begin):
                return underlying, low
        return None  # Return None if no match is found
    except Exception as e:
        print(f"{e} while find underlying regex")
        print_exc()
        return None


def find_mcx_exit_condition(symbol):
    try:
        condition = "self._ltp < self._low"
        call_or_put = re.search(r"(P|C)(?=\d+$)", symbol).group(1)
        if call_or_put == "P":
            condition = "self._ltp > self._low"
    except Exception as e:
        print(f"{e} while find mcx exit condtion")
        print_exc()
    finally:
        return condition


def send_messages(msg):
    print(msg)


def login():

    if O_SETG["trade"].get("live", 0) == 0:
        api = Paper(**O_CNFG)
    else:
        api = Finvasia(**O_CNFG)
    if api.authenticate():
        message = "api connected"
        send_messages(message)
        return api
    else:
        send_messages("Failed to authenticate. .. exiting")
        __import__("sys").exit(1)


# add a decorator to check if wait_till is past
def is_not_rate_limited(func):
    # Decorator to enforce a 1-second delay between calls
    def wrapper(*args, **kwargs):
        now = pdlm.now()
        if now < Helper.wait_till:
            blink()
        Helper.wait_till = now.add(seconds=1)
        return func(*args, **kwargs)

    return wrapper


class Helper:
    _api = None
    subscribed = {}
    completed_trades = []

    @classmethod
    @property
    def api(cls):
        if cls._api is None:
            cls._api = login()
            cls.ws = Wserver(cls._api, ["NSE:24"])
        cls.wait_till = pdlm.now().add(seconds=1)
        return cls._api

    @classmethod
    def _subscribe_till_ltp(cls, ws_key):
        try:
            quotes = cls.ws.ltp
            ltp = quotes.get(ws_key, None)
            while ltp is None:
                cls.ws.api.subscribe([ws_key], feed_type="d")
                quotes = cls.ws.ltp
                ltp = quotes.get(ws_key, None)
                timer(0.25)
        except Exception as e:
            logging.error(f"{e} while get ltp")
            print_exc()
            cls._subscribe_till_ltp(ws_key)

    @classmethod
    def history(cls, exchange, token):
        try:
            now = pdlm.now()
            fm = now.replace(hour=9, minute=0, second=0, microsecond=0).timestamp()
            to = now.replace(hour=9, minute=17, second=0, microsecond=0).timestamp()
            return cls.api.historical(exchange, token, fm, to)
        except Exception as e:
            logging.error(f"{e} in history")

    @classmethod
    def symbol_info(cls, exchange, symbol):
        try:
            # TODO undo this code
            low = False
            if cls.subscribed.get(symbol, None) is None:
                token = cls.api.instrument_symbol(exchange, symbol)
                key = exchange + "|" + str(token)
                if not low:
                    logging.debug(f"trying to get low for {symbol=} and {token=}")
                    resp = cls.history(exchange, token)
                    low = resp[-2]["intl"]
                cls.subscribed[symbol] = {
                    "symbol": symbol,
                    "key": key,
                    # "low": 0,
                    "low": low,
                    "ltp": cls._subscribe_till_ltp(key),
                }
            if cls.subscribed.get(symbol, None) is not None:
                quotes = cls.ws.ltp
                ws_key = cls.subscribed[symbol]["key"]
                cls.subscribed[symbol]["ltp"] = float(quotes[ws_key])
                return cls.subscribed[symbol]
        except Exception as e:
            logging.error(f"{e} while symbol info")
            print_exc()

    @classmethod
    def get_quotes(cls):
        try:
            quote = {}
            ltps = cls.ws.ltp
            quote = {
                symbol: ltps.get(values["key"])
                for symbol, values in cls.subscribed.items()
            }
        except Exception as e:
            logging.error(f"{e} while getting quote")
            print_exc()
        finally:
            return quote

    @classmethod
    def ltp(cls, exchange, token):
        try:
            resp = cls.api.scriptinfo(exchange, token)
            if resp is not None:
                return float(resp["lp"])
            else:
                return None
        except Exception as e:
            message = f"{e} while ltp"
            send_messages(message)
            print_exc()

    @classmethod
    def one_side(cls, bargs):
        try:
            resp = cls.api.order_place(**bargs)
            return resp
        except Exception as e:
            message = f"helper error {e} while placing order {bargs}"
            send_messages(message)
            print_exc()

    @classmethod
    def modify_order(cls, args):
        try:
            resp = cls.api.order_modify(**args)
            return resp
        except Exception as e:
            message = f"helper error {e} while modifying order"
            send_messages(message)
            print_exc()

    @classmethod
    def positions(cls):
        try:
            resp = cls.api.positions
            if resp and any(resp):
                # print(orders[0].keys())
                return resp
            return [{}]

        except Exception as e:
            send_messages(f"Error fetching positions: {e}")
            print_exc()

    @classmethod
    def orders(cls):
        try:
            orders = cls.api.orders
            if any(orders):
                # print(orders[0].keys())
                return orders
            return [{}]

        except Exception as e:
            send_messages(f"Error fetching orders: {e}")
            print_exc()

    @classmethod
    @is_not_rate_limited
    def trades(cls):
        try:
            from_api = []  # Return an empty list on failure
            from_api = cls.api.trades
        except Exception as e:
            send_messages(f"Error fetching trades: {e}")
            print_exc()
        finally:
            return from_api

    @classmethod
    def close_positions(cls):
        for pos in cls.api.positions:
            if pos["quantity"] == 0:
                continue
            else:
                quantity = abs(pos["quantity"])

            send_messages(f"trying to close {pos['symbol']}")
            if pos["quantity"] < 0:
                args = dict(
                    symbol=pos["symbol"],
                    quantity=quantity,
                    disclosed_quantity=quantity,
                    product="M",
                    side="B",
                    order_type="MKT",
                    exchange="NFO",
                    tag="close",
                )
                resp = cls.api.order_place(**args)
                send_messages(f"api responded with {resp}")
            elif quantity > 0:
                args = dict(
                    symbol=pos["symbol"],
                    quantity=quantity,
                    disclosed_quantity=quantity,
                    product="M",
                    side="S",
                    order_type="MKT",
                    exchange="NFO",
                    tag="close",
                )
                resp = cls.api.order_place(**args)
                send_messages(f"api responded with {resp}")

    @classmethod
    def pnl(cls, key="urmtom"):
        try:
            ttl = 0
            resp = [{}]
            resp = cls.api.positions
            """
            keys = [
                "symbol",
                "quantity",
                "last_price",
                "urmtom",
                "rpnl",
            ]
            """
            if any(resp):
                pd.DataFrame(resp).to_csv(S_DATA + "positions.csv", index=False)
                # calc value
                # list []
                # dict {}
                # list_of_dict = [
                # {},
                # {},
                # ]

                for pos in resp:
                    ttl += pos[key]
        except Exception as e:
            message = f"while calculating {e}"
            send_messages(f"api responded with {message}")
            print_exc()
        finally:
            return ttl


if __name__ == "__main__":
    from pprint import pprint
    import pandas as pd
    from constants import S_DATA

    try:
        Helper.api

        def trades():
            resp = Helper.trades()
            if resp:
                pd.DataFrame(resp).to_csv(S_DATA + "trades.csv", index=False)
                print(pd.DataFrame(resp))

        def orders():
            resp = Helper.orders()
            if any(resp):
                pd.DataFrame(resp).to_csv(S_DATA + "orders.csv", index=False)
                print(pd.DataFrame(resp))

        def test_history(exchange, symbol):
            token = Helper.api.instrument_symbol(exchange, symbol)
            print("token", token)
            resp = Helper.history(exchange, token)
            pprint(resp)
            print(resp[-2]["intl"], resp[-2]["time"])

        def modify():
            args = {
                "symbol": "NIFTY28NOV24C23400",
                "exchange": "NFO",
                "order_id": "24112200115699",
                "price": 0.0,
                "price_type": "MARKET",
                "quantity": 25,
            }
            resp = Helper.modify_order(args)
            print(resp)

        def margin():
            resp = Helper.api.margins
            print(resp)

        trades()
        orders()
        resp = Helper.pnl("rpnl")
        print(resp)

        rsp = Helper.history(exchange="MCX", token="447898")
        print(rsp)

        # test_history(exchange="NFO", symbol="BANKNIFTY27MAR25C50000")
    except Exception as e:
        print(e)
        print_exc()
