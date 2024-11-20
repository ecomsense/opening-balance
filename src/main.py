from constants import O_FUTL, logging, O_SETG, S_DATA
from helper import Helper
from strategy import Strategy
from toolkit.kokoo import is_time_past, kill_tmux, timer
from traceback import print_exc
from wserver import Wserver
from pprint import pprint


class Jsondb:

    F_ORDERS = S_DATA + "orders.json"
    completed_orders = []
    orders_from_api = []
    subscribed = {}

    @classmethod
    def startup(cls):
        if O_FUTL.is_file_not_2day(cls.F_ORDERS):
            # return empty list if file is not modified today
            O_FUTL.write_file(filepath=cls.F_ORDERS, content=[])
        cls.ws = Wserver(Helper.api, ["NSE:24"])

    @classmethod
    def read_buy_order_ids(cls):
        order_from_file = O_FUTL.json_fm_file(cls.F_ORDERS)
        """ extract key from list of dictionary """
        ids = []
        if order_from_file and any(order_from_file):
            ids = [order["_id"] for order in order_from_file]
            logging.debug(ids)
        return ids

    @classmethod
    def get_one(cls):
        try:
            ids = cls.read_buy_order_ids()

            new_orders = []
            cls.orders_from_api = Helper.orders()
            if cls.orders_from_api and any(cls.orders_from_api):
                """convert list to dict with order id as key"""
                new_orders = [
                    {"id": order["order_id"], "buy_order": order}
                    for order in cls.orders_from_api
                    if order["side"] == "B"
                    and order["status"] == "COMPLETE"
                    and order["order_id"] not in ids
                    and order["order_id"] not in cls.completed_orders.copy()
                ]
        except Exception as e:
            print(f"{e} while get one order")
            print_exc()
        finally:
            return new_orders

    @classmethod
    def subscribe_till_ltp(cls, ws_key):
        try:
            ltp = None
            while ltp is None:
                logging.debug("subscribing")
                cls.ws.api.subscribe([ws_key], feed_type="d")
                quotes = cls.ws.ltp
                ltp = quotes.get(ws_key, None)
        except Exception as e:
            print(f"{e} while get ltp")
        return ltp

    @classmethod
    def symbol_info(cls, exchange, symbol):
        if cls.subscribed.get(symbol, None) is None:
            token = Helper.api.instrument_symbol(exchange, symbol)
            """
            now = pdlm.now()
            fm = now.replace(hour=9, minute=15, second=0, microsecond=0).timestamp()
            to = now.().timestamp()
            resp = Helper.api.historical(exchange, token, fm, to)
            """
            key = exchange + "|" + str(token)
            cls.subscribed[symbol] = {
                "key": key,
                "low": 0,
                # "low": resp[1]["intl"],
                "ltp": cls.subscribe_till_ltp(key),
            }
            return cls.subscribed[symbol]

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
            print(f"{e} while getting quote")
        finally:
            return quote


def create_strategy():
    strgy = None
    info = None
    list_of_orders = Jsondb.get_one()
    if any(list_of_orders):
        order_item = list_of_orders[0]
        if any(order_item):
            b = order_item["buy_order"]
            info = Jsondb.symbol_info(b["exchange"], b["symbol"])
            if info:
                logging.debug("creating new strategy")
                strgy = Strategy({}, order_item["id"], order_item["buy_order"], info)
    return strgy


def init():
    try:
        logging.info("HAPPY TRADING")
        Jsondb.startup()
        while not is_time_past(O_SETG["trade"]["stop"]):
            strategies = []
            logging.debug("READ strategies from file")
            list_of_attribs: list = O_FUTL.read_file(Jsondb.F_ORDERS)
            for attribs in list_of_attribs:
                strgy = Strategy(attribs, "", {}, {})
                strategies.append(strgy)

            logging.debug("CREATE strategy from orderbook")
            strgy = create_strategy()
            if strgy:
                strategies.append(strgy)  # add to list of strgy

            write_job = []
            for strgy in strategies:
                ltps = Jsondb.get_quotes()
                logging.info(f"RUNNING {strgy._fn} for {strgy._id}")
                completed_buy_order_id = strgy.run(Jsondb.orders_from_api, ltps)
                obj_dict = strgy.__dict__
                obj_dict.pop("_orders")
                pprint(obj_dict)
                timer(1)
                if completed_buy_order_id:
                    Jsondb.completed_orders.append(completed_buy_order_id)
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
        logging.error(f"{e} while running strategy")


init()
