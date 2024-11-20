from traceback import print_exc
from stock_brokers.finvasia.finvasia import Finvasia
from toolkit.datastruct import filter_dictionary_by_keys
from constants import O_CNFG


def send_messages(msg):
    print(msg)


def login():
    api = Finvasia(**O_CNFG)
    if api.authenticate():
        message = "api connected"
        send_messages(message)
        return api
    else:
        send_messages("Failed to authenticate. .. exiting")
        __import__("sys").exit(1)


class Helper:
    _api = None

    @classmethod
    @property
    def api(cls):
        if cls._api is None:
            cls._api = login()
        return cls._api

    @classmethod
    def ltp(cls, exchange, token):
        try:
            resp = cls._api.scriptinfo(exchange, token)
            if resp is not None:
                return float(resp["lp"])
            else:
                raise ValueError("ltp is none")
        except Exception as e:
            message = f"{e} while ltp"
            send_messages(message)
            print_exc()

    @classmethod
    def one_side(cls, bargs):
        try:
            sl1 = cls._api.order_place(**bargs)
            return sl1

        except Exception as e:
            message = f"helper error {e} while placing order"
            send_messages(message)
            print_exc()

    @classmethod
    def orders(cls):
        try:
            orders_from_api = []  # Return an empty list on failure
            keys = [
                "symbol",
                "quantity",
                "side",
                "validity",
                "price",
                "trigger_price",
                "average_price",
                "filled_quantity",
                "order_id",
                "exchange",
                "exchange_order_id",
                "disclosed_quantity",
                "broker_timestamp",
                "status",
                "product",
            ]
            orders_from_api = cls.api.orders
            if orders_from_api:
                # Apply filter to each order item
                orders_from_api = [
                    filter_dictionary_by_keys(order_item, keys)
                    for order_item in orders_from_api
                ]

        except Exception as e:
            send_messages(f"Error fetching orders: {e}")
            print_exc()
        finally:
            return orders_from_api

    @classmethod
    def close_positions(cls):
        for pos in cls._api.positions:
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
                resp = cls._api.order_place(**args)
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
                resp = cls._api.order_place(**args)
                send_messages(f"api responded with {resp}")

    @classmethod
    def mtm(cls):
        try:
            pnl = 0
            positions = [{}]
            positions = cls._api.positions
            """
            keys = [
                "symbol",
                "quantity",
                "last_price",
                "urmtom",
                "rpnl",
            ]
            """
            if any(positions):
                # calc value
                for pos in positions:
                    pnl += pos["urmtom"]
        except Exception as e:
            message = f"while calculating {e}"
            send_messages(f"api responded with {message}")
        finally:
            return pnl


if __name__ == "__main__":
    from pprint import pprint
    import pandas as pd

    Helper.api
    resp = Helper.orders()
    pprint(resp)
    pd.DataFrame(resp).to_csv("orders.csv", index=False)
