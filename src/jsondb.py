import pendulum as pdlm
from constants import O_FUTL, logging
from traceback import print_exc


class Jsondb:
    now = pdlm.now("Asia/Kolkata")

    @classmethod
    def startup(cls, db_file):
        try:
            if O_FUTL.is_file_not_2day(db_file):
                # return empty list if file is not modified today
                print(f"{db_file} file not modified today")

            O_FUTL.write_file(filepath=db_file, content=[])
            cls.F_ORDERS = db_file
        except Exception as e:
            logging.error(f"{e} while startup")
            print_exc()

    @classmethod
    def read(cls):
        return O_FUTL.json_fm_file(cls.F_ORDERS)

    @classmethod
    def write(cls, write_job):
        O_FUTL.write_file(cls.F_ORDERS, write_job)

    @classmethod
    def filter_trades(cls, trades_from_api, completed_trades):
        try:
            new = []
            ids = []
            order_from_file = cls.read()
            if order_from_file and any(order_from_file):
                ids = [order["_id"] for order in order_from_file]
            if trades_from_api and any(trades_from_api):
                """convert list to dict with order id as key"""
                new = [
                    {"id": order["order_id"], "buy_order": order}
                    for order in trades_from_api
                    if order["side"] == "B"
                    and order["order_id"] not in ids
                    and order["order_id"] not in completed_trades
                    and pdlm.parse(order["broker_timestamp"]) > cls.now
                ]
        except Exception as e:
            logging.error(f"{e} while get one order")
            print_exc()
        finally:
            return new
