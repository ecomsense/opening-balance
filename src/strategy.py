"""
    Purchase price for each trade plus 5% should be auto exit separately
    Options stike chart respective 9.16 one min candle low will be stop loss
    Buy will be manual  and sell will be algo with both target and stoploss.
    Multiple trades will be triggered and to be tracked separetely.
"""

from constants import logging, O_SETG
from helper import Helper
from traceback import print_exc


class Strategy:
    def __init__(self, attribs: dict, id: str, buy_order: dict, symbol_info: dict):
        if any(attribs):
            self.__dict__.update(attribs)
        else:
            self._id = id
            self._buy_order = buy_order
            self._symbol = symbol_info["symbol"]
            self._fill_price = float(buy_order["fill_price"])
            self._low = float(symbol_info["low"])
            self._ltp = float(symbol_info["ltp"])
            self._stop = float(symbol_info["low"])
            self._condition = symbol_info["condition"]
            exchange = self._buy_order["exchange"]
            self._target = O_SETG["targets"][exchange]
            self._sell_order = ""
            self._orders = []
            self._fn = "set_target"

    def set_target(self):
        try:
            target_buffer = self._target * self._fill_price / 100
            target_virtual = self._fill_price + target_buffer
            if self._ltp < self._low and (self._buy_order["exchange"] != "MCX"):
                self._target = min(target_virtual, self._low)
                self._stop = 0.00
            else:
                self._target = target_virtual

            self._target = round(self._target / 0.05) * 0.05
            self._fn = "place_sell_order"
        except Exception as e:
            print_exc()
            print(f"{e} while set target")

    def _is_target_reached(self):
        try:
            flag = False
            for order in self._orders:
                if self._sell_order == order["order_id"]:
                    logging.info(
                        f"{self._buy_order['symbol']} target order {self._sell_order} is reached"
                    )
                    flag = True
        except Exception as e:
            logging.error(f"{e} get order from book")
            print_exc()
        finally:
            return flag

    def place_sell_order(self):
        try:
            sargs = dict(
                symbol=self._buy_order["symbol"],
                quantity=abs(int(self._buy_order["quantity"])),
                product=self._buy_order["product"],
                side="S",
                price=self._target,
                trigger_price=0,
                order_type="LIMIT",
                exchange=self._buy_order["exchange"],
                tag="exit",
            )
            logging.debug(sargs)
            self._sell_order = Helper.one_side(sargs)
            if self._sell_order is None:
                raise RuntimeError(
                    f"unable to get order number for {self._buy_order}. please manage"
                )
            else:
                self._fn = "exit_order"

            if self._stop == 0:
                return self._id

        except Exception as e:
            logging.error(f"{e} whle place sell order")
            print_exc()

    def exit_order(self):
        try:
            if self._is_target_reached():
                return self._id
            elif eval(self._condition):
                args = dict(
                    symbol=self._buy_order["symbol"],
                    order_id=self._sell_order,
                    exchange=self._buy_order["exchange"],
                    quantity=abs(int(self._buy_order["quantity"])),
                    order_type="LIMIT",
                    price=round((self._ltp / 2) / 0.05) * 0.005,
                    trigger_price=0.00,
                )
                logging.debug(f"modify order {args}")
                resp = Helper.modify_order(args)
                logging.debug(f"order id: {args['order_id']} modify {resp=}")
                return self._id

        except Exception as e:
            logging.error(f"{e} while exit order")
            print_exc()

    def run(self, orders, ltps):
        try:
            self._orders = orders
            ltp = ltps.get(self._symbol, None)
            if ltp is not None:
                self._ltp = float(ltp)
            getattr(self, self._fn)()
        except Exception as e:
            logging.error(f"{e} in run for buy order {self._id}")
            print_exc()
