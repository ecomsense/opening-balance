from utils import generate_unique_id
from stock_brokers.finvasia.finvasia import Finvasia
from constants import O_CNFG, S_DATA, O_FUTL, logging
import pandas as pd
import pendulum as plum
from traceback import print_exc

ORDER_CSV = S_DATA + "orders.csv"


class Paper(Finvasia):
    cols = [
        "order_id",
        "broker_timestamp",
        "side",
        "filled_quantity",
        "symbol",
        "remarks",
        "status",
        "fill_price",
        "last_price",
    ]
    _orders = pd.DataFrame()

    def can_move_order_to_trade(self, order_id, ltp) -> bool:
        # TODO
        # move order_id to tradebook
        # if order trigger price is below ltp
        Flag = False
        orders = self.orders
        for order in orders:
            if order["order_id"] == order_id and ltp < order["fill_price"]:
                Flag = True
                break

        if Flag:
            self._orders.loc[
                self._orders["order_id"] == order["order_id"], "status"
            ] = "COMPLETE"

        return Flag

    @property
    def trades(self):
        """returns order book with status COMPLETE"""
        if not self._orders.empty:
            filtered_df = self._orders[self._orders["status"] == "COMPLETE"]
            return filtered_df.to_dict(orient="records")
        else:
            return [{}]

    def __init__(self, user_id, password, pin, vendor_code, app_key, imei, broker=""):
        super().__init__(user_id, password, pin, vendor_code, app_key, imei, broker)
        if O_FUTL.is_file_not_2day(ORDER_CSV):
            O_FUTL.nuke_file(ORDER_CSV)

    @property
    def orders(self):
        list_of_orders = self._orders
        pd.DataFrame(list_of_orders).to_csv(ORDER_CSV, index=False)
        return list_of_orders.to_dict(orient="records")

    def order_place(self, **position_dict):
        try:
            logging.info(f"order place position dict {position_dict}")
            if not position_dict.get("order_id", None):
                order_id = generate_unique_id()
            else:
                order_id = position_dict["order_id"]

            UPPER = position_dict["order_type"][0].upper()
            is_trade = UPPER == "M" or UPPER == "L"
            fill_price = (
                position_dict["last_price"]
                if is_trade
                else position_dict["trigger_price"]
            )
            status = "COMPLETE" if is_trade else "TRIGGER PENDING"
            args = dict(
                order_id=order_id,
                broker_timestamp=plum.now().format("YYYY-MM-DD HH:mm:ss"),
                side=position_dict["side"],
                filled_quantity=int(position_dict["quantity"]),
                symbol=position_dict["symbol"],
                remarks=position_dict["tag"],
                fill_price=fill_price,
                status=status,
                last_price=position_dict["last_price"],
            )
            logging.info(f"placing order {args}")
            df = pd.DataFrame(columns=self.cols, data=[args])

            if not self._orders.empty:
                df = pd.concat([self._orders, df], ignore_index=True)
            self._orders = df
            _ = self.orders

            return order_id
        except Exception as e:
            logging.error(f"{e} exception while placing order")
            print_exc()

    def order_modify(self, args):
        if not args.get("order_type", None):
            args["order_type"] = "MARKET"

        UPPER = args["order_type"][0].upper()
        if UPPER == "M" or UPPER == "L":
            # drop row whose order_id matches
            args["tag"] = "modify"
            self._orders = self._orders[self._orders["order_id"] != args["order_id"]]
            self.order_place(**args)
        else:
            logging.info(
                "order modify for other order types not implemented for paper trading"
            )
            # TODO FIX THIS
            raise NotImplementedError(
                "order modify for other order types not implemented"
            )

    def _ord_to_pos(self, df):
        # Filter DataFrame to include only 'B' (Buy) side transactions
        buy_df = df[df["side"] == "BUY"]

        # Filter DataFrame to include only 'S' (Sell) side transactions
        sell_df = df[df["side"] == "SELL"]

        # Group by 'symbol' and sum 'filled_quantity' and 'fill_price' for 'B' side transactions
        buy_grouped = (
            buy_df.groupby("symbol")
            .agg({"filled_quantity": "sum", "fill_price": "sum"})
            .reset_index()
        )

        # Group by 'symbol' and sum 'filled_quantity' and 'fill_price' for 'S' side transactions
        sell_grouped = (
            sell_df.groupby("symbol")
            .agg({"filled_quantity": "sum", "fill_price": "sum"})
            .reset_index()
        )

        # Merge the two DataFrames on 'symbol' column with a left join
        result_df = pd.merge(
            buy_grouped,
            sell_grouped,
            on="symbol",
            suffixes=("_buy", "_sell"),
            how="outer",
        )
        print(result_df)
        # Fill NaN values with 0
        result_df.fillna(0, inplace=True)

        # Calculate the net filled quantity by subtracting 'Sell' side quantity from 'Buy' side quantity
        result_df["quantity"] = (
            result_df["filled_quantity_buy"] - result_df["filled_quantity_sell"]
        )

        # Calculate the unrealized mark-to-market (urmtom) value
        result_df["urmtom"] = result_df.apply(
            lambda row: (
                0
                if row["quantity"] == 0
                else (row["fill_price_buy"] - row["fill_price_sell"]) * row["quantity"]
            ),
            axis=1,
        )

        # Calculate the realized profit and loss (rpnl)
        result_df["rpnl"] = result_df.apply(
            lambda row: (
                row["fill_price_sell"] - row["fill_price_buy"]
                if row["quantity"] == 0
                else 0
            ),
            axis=1,
        )

        # Drop intermediate columns
        result_df.drop(
            columns=[
                "filled_quantity_buy",
                "filled_quantity_sell",
                "fill_price_buy",
                "fill_price_sell",
            ],
            inplace=True,
        )

        return result_df

    @property
    def positions(self):
        try:
            lst = []
            if __import__("os").path.getsize(ORDER_CSV) > 2:
                print(__import__("os").path.getsize(ORDER_CSV))
                df = pd.read_csv(ORDER_CSV)
                if not df.empty:
                    logging.info("df not empty")
                    df = self._ord_to_pos(df)
                    print(df)
                    lst = df.to_dict(orient="records")
        except Exception as e:
            logging.debug(f"paper positions error: {e}")
        finally:
            return lst


if __name__ == "__main__":
    from constants import O_CNFG

    paper = Paper(**O_CNFG)
    paper.order_place(
        symbol="NIFTY",
        exchange="NSE",
        quantity=1,
        side="BUY",
        product="MIS",
        order_type="MARKET",
        tag="test",
    )
