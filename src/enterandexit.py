"""
Purchase price for each trade plus 5% should be auto exit separately
Options stike chart respective 9.16 one min candle low will be stop loss
Buy will be manual  and sell will be algo with both target and stoploss.
Multiple trades will be triggered and to be tracked separetely.
"""

from constants import logging, O_SETG
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
        prefix: str,
        symbol: str,
        low: float,
        ltp: float,
        exchange: str,
        quantity: int,
        target: float,
    ):
        self._prefix = prefix
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
                    price=self._ltp + 2,
                    order_type="LMT",
                    exchange=self._exchange,
                    tag="entry",
                    last_price=self._ltp,
                )
                resp = Helper.one_side(bargs)
                if resp:
                    self._id = resp
                    self._place_sell_order()
                    self._fn = "find_fill_price"
                else:
                    logging.error(f"unable to place order for {bargs}")
        except Exception as e:
            print(f"{e} while waiting for breakout")

    def _place_sell_order(self):
        try:
            sargs = dict(
                symbol=self._symbol,
                quantity=self._quantity,
                disclosed_quantity=0,
                product="M",
                side="S",
                price=self._low - 2,
                trigger_price=self._low,
                order_type="SL-LMT",
                exchange=self._exchange,
                tag="exit",
                last_price=self._ltp,
            )
            logging.debug(sargs)
            self._sell_order = Helper.one_side(sargs)

            # Validate sell order response
            if not self._sell_order or not isinstance(self._sell_order, str):
                logging.error(f"Invalid sell order response: {self._sell_order}")
                __import__("sys").exit(1)
            else:
                logging.info(f"TARGET order for {self._id} is {self._sell_order}")

        except Exception as e:
            logging.error(f"{e} while place sell order")
            print_exc()

    def _set_target(self):
        try:
            rate_to_be_added = 0
            """
            resp = Helper.positions()
                todo
            if resp and any(resp):
                total_rpnl = sum(
                    item["rpnl"]
                    for item in resp
                    if item["symbol"].startswith(self._prefix)
                )
                if total_rpnl < 0:
                    rate_to_be_added = total_rpnl / self._quantity
            """
            target_buffer = self._target * self._fill_price / 100
            target_virtual = self._fill_price + target_buffer - rate_to_be_added
            self._target = round(target_virtual / 0.05) * 0.05
            self._fn = "exit_order"

        except Exception as e:
            print_exc()
            logging.error(f"{e} while set target")

    def find_fill_price(self):
        try:
            for order in self._orders:
                if self._id == order["order_id"]:
                    self._buy_order = order
                    self._fill_price = order["fill_price"]
                    self._set_target()
        except Exception as e:
            logging.error(f"{e} find_fill_price")
            print_exc()

    def _is_stoploss_hit(self):
        try:
            flag = False
            if O_SETG["trade"].get("live", 0) == 0:
                flag = Helper.api.can_move_order_to_trade(self._sell_order, self._ltp)
                return flag
            for order in self._orders:
                if self._sell_order == order["order_id"]:
                    logging.debug(
                        f"{self._symbol} STOP LOSS #{self._sell_order} is HIT"
                    )
                    flag = True
                else:
                    print(self._sell_order, "is compared with", order["order_id"])
            return flag
        except Exception as e:
            logging.error(f"{e} get order from book{self._orders}")
            print_exc()

    def exit_order(self):
        try:
            FLAG = False
            if self._is_stoploss_hit():
                FLAG = True
            elif self._ltp >= self._target:
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
                    last_price=self._ltp,
                )
                logging.debug(f"modify order {args}")
                resp = Helper.modify_order(args)
                logging.debug(f"order id: {args['order_id']} modify {resp=}")
                FLAG = True

            if FLAG:
                self._time_mgr.set_last_trade_time(pdlm.now("Asia/Kolkata"))
                self._is_trading_below_low = False
                self._fn = "is_trading_below_low"
            else:
                logging.debug(f"target: {self._target} < {self._ltp}")

        except Exception as e:
            logging.error(f"{e} while exit order")
            print_exc()

    def run(self, orders, ltps):
        try:
            self._orders = orders
            ltp = ltps.get(self._symbol, None)
            if ltp is not None:
                self._ltp = float(ltp)
            result = getattr(self, self._fn)()
            return result
        except Exception as e:
            logging.error(f"{e} in run for buy order {self._id}")
            print_exc()


if __name__ == "__main__":
    from helper import Helper

    def iter_tradebook(orders, search_id):
        try:
            for order in orders:
                print(order)
                if search_id == order["order_id"]:
                    print(f"{search_id} is found")
        except Exception as e:
            logging.error(f"{e} get order from book")
            print_exc()

    Helper.api
    resp = Helper.trades()
    iter_tradebook(resp, "25031900397534")
