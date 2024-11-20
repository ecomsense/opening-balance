"""
    Purchase price for each trade plus 5% should be auto exit separately
    Options stike chart respective 9.16 one min candle low will be stop loss
    Buy will be manual  and sell will be algo with both target and stoploss.
    Multiple trades will be triggered and to be tracked separetely.
"""

from constants import logging
from helper import Helper
from traceback import print_exc


class Strategy:
    def __init__(self, attribs: dict, id: str, buy_order: dict, symbol_info: dict):
        if any(attribs):
            self.__dict__.update(attribs)
        else:
            self._id = id
            self._buy_order = buy_order
            self._symbol = buy_order["symbol"]
            self._average_price = float(buy_order["average_price"])
            self._low = float(symbol_info["low"])
            self._ltp = symbol_info["ltp"]
            self._target = 2
            self._sell_order = ""
            self._orders = []
            self._fn = "set_target"

    def set_target(self):
        try:
            target_buffer = self._target * self._average_price / 100
            target_virtual = self._average_price + target_buffer
            if self._average_price < self._low:
                self._target = min(target_virtual, self._low)
            else:
                self._target = target_virtual
            self._fn = "place_sell_order"
        except Exception as e:
            print_exc()
            print(f"{e} while set target")

    def place_sell_order(self):
        try:
            sargs = dict(
                symbol=self._symbol,
                quantity=abs(int(self._buy_order["quantity"])),
                product=self._buy_order["product"],
                side="S",
                price=self._target,
                trigger_price=0,
                order_type="LMT",
                exchange=self._buy_order["exchange"],
                tag="exit",
            )
            logging.debug(sargs)
            self._sell_order = Helper.one_side(sargs)
            if self._sell_order is None:
                raise f"unable to get order number for {self._buy_order}. please manage"
            else:
                self._fn = "exit_order"
        except Exception as e:
            print(e)
            print_exc()

    def _get_order_from_book(self, order_id):
        for order in self._orders:
            if order_id == order["order_id"]:
                return order
        return {}

    def exit_order(self):
        try:
            order = self._get_order_from_book(self._sell_order)
            if order["status"].upper() == "COMPLETE":
                logging.info(
                    f"{self._symbol} target {self._sell_order} "
                    + f"status is {order['status']}"
                )
                return self._id
        except Exception as e:
            print(f"{e} while exit order")
            print_exc()

    def run(self, orders, ltps):
        try:
            self._orders = orders
            self._ltp = ltps.get(self._symbol, None)
            getattr(self, self._fn)()
        except Exception as e:
            print(f"{e} in run")
            print_exc()
