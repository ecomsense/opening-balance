from constants import logging, O_SETG
from helper import Helper
from enterandexit import EnterAndExit
from toolkit.kokoo import is_time_past, timer
from traceback import print_exc
from symbols import Symbols, dct_sym
from typing import Any, Literal


def get_symbols_to_trade() -> dict[str, Any]:
    """
    Retrieves tokens for all trading symbols.

    This function filters trading symbols based on a blacklist and retrieves tokens
    for each symbol using the `Symbols` class. It calculates the at-the-money (ATM)
    strike price based on the latest traded price (LTP) of the underlying asset and
    fetches the corresponding tokens.

    Returns:
        A dictionary where keys are trading symbols (str), and values contain
        symbol-specific configuration details from user settings.

    Raises:
        Exception: If an error occurs during token retrieval.
    """
    try:
        black_list = ["log", "trade", "target", "MCX"]
        symbols_to_trade = {k: v for k, v in O_SETG.items() if k not in black_list}
        logging.info(symbols_to_trade)
        return symbols_to_trade
    except Exception as e:
        logging.error(f"{e} while init")
        return {}


def find_instrument_tokens_to_trade(symbols_to_trade) -> dict[str, Any]:
    """
    get instrument tokens from broker for each symbol to trade and merge them together
    """
    try:
        tokens_of_all_trading_symbols = {}
        for k, v in symbols_to_trade.items():
            sym = Symbols(
                option_exchange=v["option_exchange"],
                base=v["base"],
                expiry=v["expiry"],
            )
            sym.get_exchange_token_map_finvasia()
            # find ltp for underlying
            exchange = dct_sym[k]["exchange"]
            token = dct_sym[k]["token"]
            ltp_for_underlying = Helper.ltp(exchange, token)
            # find from ltp
            atm = sym.get_atm(ltp_for_underlying)
            # find tokens from ltp
            logging.info(f"atm {atm} for underlying {k} from {ltp_for_underlying}")
            tokens_of_all_trading_symbols.update(sym.get_tokens(atm))
        return tokens_of_all_trading_symbols
    except Exception as e:
        logging.error(f"{e} while find instrument to trade")
        print_exc()
        return {}


def find_trading_symbol_to_trade(
    ce_or_pe: Literal["C", "P"], symbol_item: dict[str, Any]
) -> dict[str, Any]:
    """
    find trading symbol to trade based on the atm given the
    symbol item

    Args:
        ce_or_pe (Literal["C", "P"]): A string that denotes Call or Put
        symbol_item (dict[str, Any]): symbol item selected to find trading symbol

    Returns:
        symbol_info: trading symbol

    Raises:
        Exception: If there is any error

    """
    try:
        for k, v in symbol_item.items():
            sym = Symbols(
                option_exchange=v["option_exchange"],
                base=v["base"],
                expiry=v["expiry"],
            )
            exchange = dct_sym[k]["exchange"]
            token = dct_sym[k]["token"]
            resp = Helper.history(exchange, token)
            if resp and any(resp):
                low = resp[-1]["intl"]
                # find from ltp
                atm = sym.get_atm(float(low))
                # find tokens from ltp
                logging.info(f"atm {atm} for underlying {k} from {low}")
                result = sym.find_option_by_distance(
                    atm=atm,
                    distance=v["moneyness"],
                    c_or_p=ce_or_pe,
                    dct_symbols=Helper.tokens_for_all_trading_symbols,
                )
                symbol_info: dict[str, Any] = Helper.symbol_info(
                    v["option_exchange"], result["symbol"]
                )
                return symbol_info
            else:
                exc = f"History {resp} is empty for {exchange=} and {token=}"
                raise Exception(exc)
        return {}
    except Exception as e:
        logging.error(f"{e} while finding the trading symbol")
        print_exc()
        return {}


def create_strategies(symbols_to_trade: dict[str, Any]) -> list:
    """
    Creates a list of strategies based on the provided symbols_to_trade.

    Args:
        symbols_to_trade (dict[str, Any]): A dictionary containing all symbols information to trade

    Returns:
        strategies: A list of EnterAndExit objects

    Raises:
        Exception: If there is any error
    """
    try:
        strategies = []
        for k, v in symbols_to_trade.items():
            lst_of_option_type = ["C", "P"]
            for option_type in lst_of_option_type:
                symbol_item = {k: v}
                symbol_info = find_trading_symbol_to_trade(option_type, symbol_item)
                if any(symbol_info):
                    strgy = EnterAndExit(
                        prefix=k,
                        symbol=symbol_info["symbol"],
                        low=float(symbol_info["low"]),
                        ltp=symbol_info["ltp"],
                        exchange=v["option_exchange"],
                        quantity=v["quantity"],
                        target=v["target"],
                        txn=v["txn"],
                    )
                    strategies.append(strgy)
                else:
                    raise Exception(f"Could not find trading symbol for {symbol_item}")
        return strategies
    except Exception as e:
        logging.error(f"{e} while creating the strategies")
        return []


def main():
    try:
        # login to broker api
        Helper.api

        # get user selected symbols to trade
        symbols_to_trade = get_symbols_to_trade()

        while not is_time_past(O_SETG["trade"]["start"]):
            print(f"waiting till {O_SETG['trade']['start']}")

        # get all the tokens we will be trading
        Helper.tokens_for_all_trading_symbols = find_instrument_tokens_to_trade(
            symbols_to_trade
        )

        # make strategy oject for each symbol selected
        strategies: list[EnterAndExit] = create_strategies(symbols_to_trade)

        while not is_time_past(O_SETG["trade"]["stop"]):
            for strgy in strategies:
                msg = f"{strgy._symbol} ltp:{strgy._ltp} low:{strgy._low} {strgy._fn}"
                resp = strgy.run(Helper.trades(), Helper.get_quotes())
                logging.info(f"{msg} returned {resp}")
    except KeyboardInterrupt:
        __import__("sys").exit()
    except Exception as e:
        print_exc()
        logging.error(f"{e} while init")


if __name__ == "__main__":
    main()
