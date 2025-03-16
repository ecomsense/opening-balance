"""
Purchase price for each trade plus 5% should be auto exit separately
Options stike chart respective 9.16 one min candle low will be stop loss
Buy will be manual  and sell will be algo with both target and stoploss.
Multiple trades will be triggered and to be tracked separetely.
"""

from constants import logging
from helper import Helper
from traceback import print_exc
from timemanager import TimeManager
import pendulum as pdlm


class EnterAndExit:
    _id = None
    _buy_order = {}
    _fill_price = 0
    _sell_order = None
    _orders = []
    _is_trading_below_low = False
    _time_mgr = TimeManager()

    def __init__(
        self,
        symbol: str,
        low: float,
        ltp: float,
        exchange: str,
        quantity: int,
        target: float,
    ):
        self._symbol = symbol
        self._low = low
        self._ltp = ltp
        self._stop = low
        self._exchange = exchange
        self._target = target
        self._quantity = quantity
        self._fn = "is_trading_below_low"

    def is_trading_below_low(self) -> bool:
        if self._ltp < self._low:
            self._is_trading_below_low = True
            self._fn = "wait_for_breakout"
        return self._is_trading_below_low

    def wait_for_breakout(self):
        try:
            if self._ltp > self._low and self._time_mgr.can_trade:
                bargs = dict(
                    symbol=self._symbol,
                    quantity=self._quantity,
                    product="M",
                    side="B",
                    price=0,
                    order_type="MKT",
                    exchange=self._exchange,
                    tag="entry",
                )
                logging.debug(bargs)
                resp = Helper.one_side(bargs)
                if resp:
                    self._id = resp
                    self._fn = "find_fill_price"
        except Exception as e:
            print(f"{e} while waiting for breakout")

    def find_fill_price(self):
        try:
            for order in self._orders:
                if self._id == order["order_id"]:
                    self._buy_order = order
                    self._fill_price = order["fill_price"]
                    self._fn = "place_sell_order"
        except Exception as e:
            logging.error(f"{e} find_fill_price")

    def _set_target_and_stop(self):
        try:
            target_buffer = self._target * self._fill_price / 100
            target_virtual = self._fill_price + target_buffer
            self._target = target_virtual
            """
            if self._buy_order["exchange"] != "MCX":
                if self._fill_price < self._low:
                    self._target = min(target_virtual, self._low)

                # helow two lines added from above
            if self._fill_price < self._low:
                self._target = min(target_virtual, self._low)
                self._stop = 0.00
            """
            self._target = round(self._target / 0.05) * 0.05

        except Exception as e:
            print_exc()
            print(f"{e} while set target")

    def _is_target_reached(self):
        try:
            flag = False
            for order in self._orders:
                if self._sell_order == order["order_id"]:
                    logging.debug(
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
            self._set_target_and_stop()
            self._fn = "exit_order"
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

            # Validate sell order response
            if not self._sell_order or not isinstance(self._sell_order, str):
                logging.error(f"Invalid sell order response: {self._sell_order}")
                __import__("sys").exit(1)
            else:
                logging.info(
                    f"TARGET order for {self._buy_order} is {self._sell_order}"
                )

        except Exception as e:
            logging.error(f"{e} while place sell order")
            print_exc()

    def exit_order(self):
        try:
            FLAG = False
            if self._is_target_reached():
                FLAG = True
            elif self._ltp < self._stop:
                exit_buffer = 2 * self._ltp / 100
                exit_virtual = self._ltp - exit_buffer
                args = dict(
                    symbol=self._buy_order["symbol"],
                    order_id=self._sell_order,
                    exchange=self._buy_order["exchange"],
                    quantity=abs(int(self._buy_order["quantity"])),
                    order_type="LIMIT",
                    price=round(exit_virtual / 0.05) * 0.05,
                    trigger_price=0.00,
                )
                logging.debug(f"modify order {args}")
                resp = Helper.modify_order(args)
                logging.debug(f"order id: {args['order_id']} modify {resp=}")

            if FLAG:
                self._time_mgr.set_last_trade_time(pdlm.now("Asia/Kolkata"))
                self._is_trading_below_low = False
                self._fn = "is_trading_below_low"

        except Exception as e:
            logging.error(f"{e} while exit order")
            print_exc()

    def run(self, orders, ltps):
        try:
            print(ltps)
            self._orders = orders
            ltp = ltps.get(self._symbol, None)
            if ltp is not None:
                self._ltp = float(ltp)
            result = getattr(self, self._fn)()
            return result
        except Exception as e:
            logging.error(f"{e} in run for buy order {self._id}")
            print_exc()
