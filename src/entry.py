# Optionally, if you'd like to store the data in a pandas DataFrame for better readability
import pandas as pd

from constants import O_SETG

# pprint is optional .. it pretty prints
# complex data types
from pprint import pprint
from typing import Dict, Optional

"""

All 3 yes

1) Stock Universe
        NIFTY, BANKNIFY, NATURALGAS


9.16 low IS 100
(comes from historical data)

WHEN TO BUY:

ONLY IF THE PRICE CROSSES FROM BELOW TO ABOVE i.e 99 to 100 buy should happen (standard buy condition)
Also, if the price opening price is above 100. Do not buy.
If ltp < 100 of previous tick and ltp of current tick >= 100
dont buy in the same candle that you covered a trade

WHEN TO SELL: (MY STOP LOSS)
exit position if the pricess crosses below 100 ie. 99.9 (square off)

Rentry condition:

when buy condition meets. only one buy per one minute candle (this should be flexible option to change to 3 or 5 etc).


Target will be accumulated loss plus 10%



program logic



login and get token
start websocket and subscribe for required symbols
get option chain for all the symbols we are going to trade
filter by symbol, ce_or_pe
find
        scan for options that are nearest to the target price
if found
        get historical data for the found option
        get the second candle low.

        Def repeat():
                Read the ltp
                If it is below low
                        store the ltp
                        read the ltp
                        if it is above or equal to ltp (take trade)

        def is_symbol_closest_to_target_price(symbol):
                return True




  nifty 2 trades  2000 profit
banknifty 1 trade 3000 loss
natgas 3 trade 6000 loss

                qty   m2m    utom    aprice
nifty23marpe21k  1  5000     0
nifty23marce21k  0    0      -3000
nifty2marpe24k  1   -300     0     :show

whenever
portfolio is below 2% or above 5% close all the trades

capital 1L
pfolio_stop 2%
pfolio_target 5%
"""


class BeautifulClass:

    def __init__(self) -> None:
        print("no neeed to call me")


class SomeClass:
    def __init__(self, option_exchange: str, base: str, expiry: str):
        self._option_exchange = option_exchange
        self._base = base
        self.expiry = expiry
        self.csvfile = f"../data/{self._option_exchange}_symbols.csv"

    def get_exchange_token_map_finvasia(self):
        if Fileutils().is_file_not_2day(self.csvfile):
            url = f"https://api.shoonya.com/{self._option_exchange}_symbols.txt.zip"
            print(f"{url}")
            df = pd.read_csv(url)
            # filter the response
            df = df[
                (df["Exchange"] == self._option_exchange)
                # & (df["TradingSymbol"].str.contains(self._base + self.expiry))
            ][["Token", "TradingSymbol"]]
            # split columns with necessary values
            df[["Symbol", "Expiry", "OptionType", "StrikePrice"]] = df[
                "TradingSymbol"
            ].str.extract(r"([A-Z]+)(\d+[A-Z]+\d+)([CP])(\d+)")
            df.to_csv(self.csvfile, index=False)

    def get_atm(self, ltp) -> int:
        current_strike = ltp - (ltp % dct_sym[self._base]["diff"])
        next_higher_strike = current_strike + dct_sym[self._base]["diff"]
        if ltp - current_strike < next_higher_strike - ltp:
            return int(current_strike)
        return int(next_higher_strike)

    def get_tokens(self, strike):
        df = pd.read_csv(self.csvfile)
        lst = []
        lst.append(self._base + self.expiry + "C" + str(strike))
        lst.append(self._base + self.expiry + "P" + str(strike))
        for v in range(1, dct_sym[self._base]["depth"]):
            lst.append(
                self._base
                + self.expiry
                + "C"
                + str(strike + v * dct_sym[self._base]["diff"])
            )
            lst.append(
                self._base
                + self.expiry
                + "P"
                + str(strike + v * dct_sym[self._base]["diff"])
            )
            lst.append(
                self._base
                + self.expiry
                + "C"
                + str(strike - v * dct_sym[self._base]["diff"])
            )
            lst.append(
                self._base
                + self.expiry
                + "P"
                + str(strike - v * dct_sym[self._base]["diff"])
            )

        df["Exchange"] = self._option_exchange
        tokens_found = (
            df[df["TradingSymbol"].isin(lst)]
            .assign(tknexc=df["Exchange"] + "|" + df["Token"].astype(str))[
                ["tknexc", "TradingSymbol"]
            ]
            .set_index("tknexc")
        )
        dct = tokens_found.to_dict()
        return dct["TradingSymbol"]

    def find_closest_premium(
        self, quotes: Dict[str, float], premium: float, contains: str
    ) -> Optional[str]:
        contains = self.expiry + contains
        # Create a dictionary to store symbol to absolute difference mapping
        symbol_differences: Dict[str, float] = {}

        for base, ltp in quotes.items():
            if re.search(re.escape(contains), base):
                difference = abs(ltp - premium)
                symbol_differences[base] = difference

        # Find the symbol with the lowest difference
        closest_symbol = min(
            symbol_differences, key=symbol_differences.get, default=None
        )

        return closest_symbol


class OptionSymbolManager:
    def __init__(self, option_exchange: str, base: str, expiry: str):
        self._option_exchange = option_exchange
        self._base = base
        self.expiry = expiry
        self.csvfile = f"../data/{self._option_exchange}_symbols.csv"

    def get_all_trading_symbols(self):
        # This method should return a list of all the trading symbols
        df = pd.read_csv(self.csvfile)
        return df["TradingSymbol"].tolist()

    def update_symbol_info(self):
        # Fetch all trading symbols
        symbols = self.get_all_trading_symbols()

        # Update the symbol_info_with_low in Helper class
        Helper.update_symbol_info_with_low(symbols)

    def find_low_for_symbols(self):
        # Initialize a dictionary to store symbol and its corresponding low price
        symbol_info_with_low = {}

        # Assuming you have a list of trading symbols that you want to process
        symbols = self.get_all_trading_symbols()

        # Fetch the low price for each symbol
        for symbol in symbols:
            low_price = Helper.get_low_price(
                symbol
            )  # Assuming Helper.get_low_price(symbol) is defined
            symbol_info_with_low[symbol] = (
                low_price  # Store the low price in the dictionary
            )

        symbol_info_df = pd.DataFrame(
            symbol_info_with_low.items(), columns=["TradingSymbol", "LowPrice"]
        )

        # Optionally, save the DataFrame to a CSV file
        symbol_info_df.to_csv("symbol_info_with_low.csv", index=False)

        return symbol_info_with_low


def initialize():
    pprint(O_SETG)
    keys = ["log", "targets", "trade", "MCX"]
    four_key_items = {
        key: value
        for key, value in O_SETG.items()
        if isinstance(value, dict) and key not in keys
    }
    print(f"{four_key_items=}")
    return four_key_items


def get_tokens_from_symbols():
    symbols_for_trade = initialize()

    # from Symbols class find the token of trading symbols
    symbol_info: dict = "complete the code here"


def find_symbol_in_moneyness(self, tradingsymbol, ce_or_pe, price_type):
    def find_strike(ce_or_pe):
        search = self._base + self.expiry + ce_or_pe
        # find the remaining string in the symbol after removing search
        strike = re.sub(search, "", tradingsymbol)
        return search, int(strike)

    search, strike = find_strike(ce_or_pe)
    if ce_or_pe == "C":
        if price_type == "ITM":
            return search + str(strike - dct_sym[self._base]["diff"])
        else:
            return search + str(strike + dct_sym[self._base]["diff"])
    else:
        if price_type == "ITM":
            return search + str(strike + dct_sym[self._base]["diff"])
        else:
            return search + str(strike - dct_sym[self._base]["diff"])


if __name__ == "__main__":
    from helper import Helper

    # Now, you can access the symbol_info_with_low property anywhere:
    option_manager = OptionSymbolManager(
        option_exchange="NSE", base="NIFTY", expiry="23Mar2025"
    )
    option_manager.update_symbol_info()  # Update the symbol info

    # Retrieve the updated symbol info with low prices
    print(Helper.get_symbol_info_with_low())
