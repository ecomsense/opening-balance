from constants import logging, O_SETG, S_DATA
from helper import Helper
from strategy import Strategy
from toolkit.kokoo import is_time_past, timer
from traceback import print_exc
from pprint import pprint
from jsondb import Jsondb


def run_strategies(strategies, trades_from_api):
    try:
        write_job = []
        for strgy in strategies:
            ltps = Helper.get_quotes()
            logging.info(f"RUNNING {strgy._fn} for {strgy._id}")
            completed_buy_order_id = strgy.run(trades_from_api, ltps)
            logging.debug(f"{completed_buy_order_id=} while run strategies")
            obj_dict = strgy.__dict__
            obj_dict.pop("_orders")
            pprint(obj_dict)
            timer(1)
            if completed_buy_order_id:
                logging.debug(f" order buy {completed_buy_order_id} completed")
                Helper.completed_trades.append(completed_buy_order_id)
            else:
                write_job.append(obj_dict)

        if any(write_job):
            Jsondb.write(write_job)
    except Exception as e:
        print_exc()
        logging.error(f"{e} while run_strategies")


def strategies_from_file():
    try:
        strategies = []
        list_of_attribs = Jsondb.read()
        if list_of_attribs and any(list_of_attribs):
            for attribs in list_of_attribs:
                strgy = Strategy(attribs, "", {}, {})
                strategies.append(strgy)
        return strategies
    except Exception as e:
        logging.error(f"{e} while strategies_from_file")
        print_exc()


def create_strategy(list_of_orders):
    try:
        strgy = None
        info = None
        if any(list_of_orders):
            order_item = list_of_orders[0]
            if any(order_item):
                b = order_item["buy_order"]
                info = Helper.symbol_info(b["exchange"], b["symbol"])
                if info:
                    logging.info(f"CREATE new strategy {order_item['id']} {info}")
                    strgy = Strategy(
                        {}, order_item["id"], order_item["buy_order"], info
                    )
        return strgy
    except Exception as e:
        logging.error(f"{e} while creating strategy")
        print_exc()


def _init():
    logging.info("HAPPY TRADING")
    F_ORDERS = S_DATA + "orders.json"
    Jsondb.startup(F_ORDERS)
    Helper.api


def main():
    try:
        _init()
        while not is_time_past(O_SETG["trade"]["stop"]):
            strategies = strategies_from_file()
            trades_from_api = Helper.trades()
            list_of_trades = Jsondb.filter_trades(
                trades_from_api, Helper.completed_trades
            )
            strgy = create_strategy(list_of_trades)
            if strgy:
                strategies.append(strgy)
            run_strategies(strategies, trades_from_api)
    except KeyboardInterrupt:
        __import__("sys").exit()
    except Exception as e:
        print_exc()
        logging.error(f"{e} while init")


if __name__ == "__main__":
    main()
