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
    _target_price = None
    _removable = False
    _time_mgr = TimeManager()

    def __init__(
        self,
        prefix: str,
        symbol: str,
        low: float,
        ltp: float,
        exchange: str,
        target: float,
        quantity: int,
        txn: int,
    ):
        self._prefix = prefix
        self._symbol = symbol
        self._low = low
        self._ltp = ltp
        self._stop = low
        self._exchange = exchange
        self._target = target
        self._quantity = quantity
        self._txn = txn
        self._fn = "is_trading_below_low"

    def is_trading_below_low(self) -> bool:
        """checks if symbol is trading below or equal to low and return true or false"""
        if self._ltp <= self._low:
            self._is_trading_below_low = True
            self._fn = "wait_for_breakout"
        return self._is_trading_below_low

    def wait_for_breakout(self):
        """if trading below above is true, we wait for ltp to be equal or greater than low"""
        try:
            if self._ltp >= self._low and self._time_mgr.can_trade:
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
                tag="stoploss",
                last_price=self._ltp,
            )
            logging.debug(sargs)
            self._sell_order = Helper.one_side(sargs)

            # Validate sell order response
            if not self._sell_order or not isinstance(self._sell_order, str):
                logging.error(f"Invalid stop order response: {self._sell_order}")
                __import__("sys").exit(1)
            else:
                logging.info(f"TARGET order for {self._id} is {self._sell_order}")

        except Exception as e:
            logging.error(f"{e} while place sell order")
            print_exc()

    def _set_target(self):
        try:
            rate_to_be_added = 0
            logging.debug(f"setting target for {self._symbol}")
            resp = Helper.positions()
            if resp and any(resp):
                total_rpnl = sum(
                    item["rpnl"]
                    for item in resp
                    if item["symbol"].startswith(self._prefix)
                )
                logging.debug(f"looking to add loss if any {total_rpnl=}")
                if total_rpnl < 0:
                    count = len(
                        [
                            order
                            for order in self._orders
                            if order["symbol"].startswith(self._prefix)
                        ]
                    )
                    rate_to_be_added = abs(total_rpnl) / self._quantity
                    txn_cost = count * self._txn / 2
                    logging.debug(
                        f"txn: {txn_cost} = orders:{count} * txn_rate:{self._txn} / 2"
                    )
                    rate_to_be_added += txn_cost

                    logging.debug(
                        f"final {rate_to_be_added=} because of negative {total_rpnl=} and {txn_cost=} "
                    )
            else:
                logging.warning(f"no positions for {self._symbol} in {resp}")

            target_buffer = self._target * self._fill_price / 100
            target_virtual = self._fill_price + target_buffer + rate_to_be_added
            self._target_price = round(target_virtual / 0.05) * 0.05
            self._fn = "try_exiting_trade"

        except Exception as e:
            print_exc()
            logging.error(f"{e} while set target")

    def find_fill_price(self):
        try:
            for order in self._orders:
                if self._id == order["order_id"]:
                    self._buy_order = order
                    self._fill_price = float(order["fill_price"])
                    self._set_target()
        except Exception as e:
            logging.error(f"{e} find_fill_price")
            print_exc()

    def _is_stoploss_hit(self):
        try:
            flag = False
            if O_SETG["trade"].get("live", 0) == 0:
                logging.debug("CHECKING STOP IN PAPER MODE")
                flag = Helper.api.can_move_order_to_trade(self._sell_order, self._ltp)
                return flag
            for order in self._orders:
                if self._sell_order == order["order_id"]:
                    logging.debug(
                        f"{self._symbol} STOP LOSS #{self._sell_order} is HIT"
                    )
                    flag = True
                    break
                else:
                    logging.debug(
                        f"STOP LOSS #{self._sell_order} is NOT EQUAL to {order['order_id']}"
                    )
            return flag
        except Exception as e:
            logging.error(f"{e} get order from book{self._orders}")
            print_exc()

    def _get_modify_params(self):
        exit_buffer = 2 * self._ltp / 100
        exit_virtual = self._ltp - exit_buffer
        return dict(
            symbol=self._symbol,
            quantity=self._quantity,
            disclosed_quantity=0,
            product="M",
            side="S",
            price=round(exit_virtual / 0.05) * 0.05,
            trigger_price=0.0,
            order_type="LIMIT",
            exchange=self._exchange,
            tag="target_reached",
            last_price=self._ltp,
            order_id=self._sell_order,
        )

    def try_exiting_trade(self):
        try:
            if self._is_stoploss_hit():
                self._time_mgr.set_last_trade_time(pdlm.now("Asia/Kolkata"))
                self._is_trading_below_low = False
                self._fn = "is_trading_below_low"
            elif self._ltp >= self._target_price:
                args = self._get_modify_params()
                logging.debug(f"modify order {args}")
                resp = Helper.modify_order(args)
                logging.debug(f"order id: {args['order_id']} modify {resp=}")
                self._fn = "remove_me"
                return self._prefix

            else:
                msg = (
                    f"{self._symbol} target: {self._target_price} < {self._ltp} > sl: {self._low} "
                    f"Remaining to target: {int(((self._target_price - self._ltp) / (self._target_price - self._low)) * 100)}%"
                )
                logging.info(msg)

        except Exception as e:
            logging.error(f"{e} while exit order")
            print_exc()

    def remove_me(self):

        if self._fn == "find_fill_price":
            logging.info(f"{self._symbol} going to REMOVE after finding fill price")
            self.find_fill_price()
            self.remove_me()
        if self._fn == "try_exiting_trade":
            logging.info(f"{self._symbol} going to REMOVE after force modify")
            args = self._get_modify_params()
            args["tag"] = "removing"
            resp = Helper.modify_order(args)
            logging.debug(f"order id: {args['order_id']} modify {resp=}")
        else:
            logging.info(f"{self._symbol} going to REMOVE without waiting for breakout")

        self._removable = True

    def run(self, orders, ltps, prefixes: list):
        try:
            self._orders = orders
            ltp = ltps.get(self._symbol, None)
            if ltp is not None:
                self._ltp = float(ltp)
            if self._prefix in prefixes:
                self.remove_me()
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
