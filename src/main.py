from constants import O_FUTL, logging, O_SETG, S_DATA
from helper import Helper
from strategy import Strategy
from toolkit.kokoo import is_time_past, kill_tmux, timer
from traceback import print_exc
from wserver import Wserver
from pprint import pprint
import pendulum as pdlm


class Jsondb:
    F_ORDERS = S_DATA + "orders.json"
    completed_trades = []
    trades_from_api = []
    subscribed = {}
    now = pdlm.now("Asia/Kolkata")

    @classmethod
    def startup(cls):
        try:
            if O_FUTL.is_file_not_2day(cls.F_ORDERS):
                # return empty list if file is not modified today
                O_FUTL.write_file(filepath=cls.F_ORDERS, content=[])
            else:
                O_FUTL.write_file(filepath=cls.F_ORDERS, content=[])

            cls.ws = Wserver(Helper.api, ["NSE:24"])
        except Exception as e:
            logging.error(f"{e} while startup")
            print_exc()

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
            return ltp
        except Exception as e:
            logging.error(f"{e} while get ltp")
            print_exc()
            cls._subscribe_till_ltp(ws_key)

    @classmethod
    def symbol_info(cls, exchange, symbol):
        try:
            if cls.subscribed.get(symbol, None) is None:
                token = Helper.api.instrument_symbol(exchange, symbol)
                now = pdlm.now()
                fm = now.replace(hour=9, minute=0, second=0, microsecond=0).timestamp()
                to = now.replace(hour=9, minute=17, second=0, microsecond=0).timestamp()
                resp = Helper.api.historical(exchange, token, fm, to)
                key = exchange + "|" + str(token)
                cls.subscribed[symbol] = {
                    "key": key,
                    # "low": 0,
                    "low": resp[-2]["intl"],
                    "ltp": cls._subscribe_till_ltp(key),
                }
            if cls.subscribed.get(symbol, None) is not None:
                if cls.subscribed[symbol]["ltp"] is None:
                    raise ValueError("Ltp cannot be None")
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
    def get_one(cls):
        try:
            new = []
            order_from_file = O_FUTL.json_fm_file(cls.F_ORDERS)
            ids = read_buy_order_ids(order_from_file)
            cls.trades_from_api = Helper.trades()
            if cls.trades_from_api and any(cls.trades_from_api):
                """convert list to dict with order id as key"""
                new = [
                    {"id": order["order_id"], "buy_order": order}
                    for order in cls.trades_from_api
                    if order["side"] == "B"
                    and order["order_id"] not in ids
                    and order["order_id"] not in cls.completed_trades.copy()
                    and pdlm.parse(order["broker_timestamp"]) > cls.now
                ]
        except Exception as e:
            logging.error(f"{e} while get one order")
            print_exc()
        finally:
            return new


def read_buy_order_ids(order_from_file):
    try:
        ids = []
        if order_from_file and any(order_from_file):
            ids = [order["_id"] for order in order_from_file]
            logging.debug(ids)
    except Exception as e:
        logging.error(f"{e} while read_buy_order_ids")
        print_exc()
    finally:
        return ids


def read_from_file():
    try:
        strategies = []
        logging.debug("READ strategies from file")
        list_of_attribs: list = O_FUTL.json_fm_file(Jsondb.F_ORDERS)
        for attribs in list_of_attribs:
            strgy = Strategy(attribs, "", {}, {})
            strategies.append(strgy)
        return strategies
    except Exception as e:
        logging.error(f"{e} while read_from_file")
        print_exc()


def create_strategy():
    try:
        strgy = None
        info = None
        list_of_orders = Jsondb.get_one()
        if any(list_of_orders):
            order_item = list_of_orders[0]
            if any(order_item):
                b = order_item["buy_order"]
                info = Jsondb.symbol_info(b["exchange"], b["symbol"])
                if info:
                    logging.info(f"CREATE new strategy {order_item['id']}")
                    strgy = Strategy(
                        {}, order_item["id"], order_item["buy_order"], info
                    )
        return strgy
    except Exception as e:
        logging.error(f"{e} while creating strategy")
        print_exc()


def init():
    try:
        logging.info("HAPPY TRADING")
        Jsondb.startup()
        while not is_time_past(O_SETG["trade"]["stop"]):
            strategies = read_from_file()

            strgy = create_strategy()
            if strgy:
                strategies.append(strgy)  # add to list of strgy

            write_job = []
            for strgy in strategies:
                ltps = Jsondb.get_quotes()
                logging.info(f"RUNNING {strgy._fn} for {strgy._id}")
                completed_buy_order_id = strgy.run(Jsondb.trades_from_api, ltps)
                obj_dict = strgy.__dict__
                obj_dict.pop("_orders")
                pprint(obj_dict)
                timer(1)
                if completed_buy_order_id:
                    Jsondb.completed_trades.append(completed_buy_order_id)
                else:
                    write_job.append(obj_dict)

            if any(write_job):
                O_FUTL.write_file(Jsondb.F_ORDERS, write_job)
            timer(1)
        else:
            kill_tmux()
    except KeyboardInterrupt:
        __import__("sys").exit()
    except Exception as e:
        print_exc()
        logging.error(f"{e} while init")


init()
