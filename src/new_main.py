from constants import logging, O_SETG
from helper import Helper
from enterandexit import EnterAndExit
from toolkit.kokoo import is_time_past, timer
from traceback import print_exc
from pprint import pprint
from symbols import Symbols, dct_sym


def _init():
    try:
        Helper.api
        tokens_of_all_trading_symbols = {}
        black_list = ["log", "trade", "target", "MCX"]
        SYMBOLS_TO_TRADE = {k: v for k, v in O_SETG.items() if k not in black_list}
        logging.info(SYMBOLS_TO_TRADE)
        for k, v in SYMBOLS_TO_TRADE.items():
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
        Helper.tokens_for_all_trading_symbols = tokens_of_all_trading_symbols
        return SYMBOLS_TO_TRADE
    except Exception as e:
        print(f"{e} while init")


def find_trading_symbol_to_trade(ce_or_pe, kwargs):
    # TODO kwargs should be removed and just the value need to be passed
    for k, v in kwargs.items():
        print(ce_or_pe, v)
    sym = Symbols(
        option_exchange=v["option_exchange"],
        base=v["base"],
        expiry=v["expiry"],
    )
    exchange = dct_sym[k]["exchange"]
    token = dct_sym[k]["token"]
    ltp_for_underlying = Helper.ltp(exchange, token)
    # find from ltp
    atm = sym.get_atm(ltp_for_underlying)
    # find tokens from ltp
    logging.info(f"atm {atm} for underlying {k} from {ltp_for_underlying}")
    result = sym.find_option_by_distance(
        atm=atm,
        distance=v["moneyness"],
        c_or_p=ce_or_pe,
        dct_symbols=Helper.tokens_for_all_trading_symbols,
    )
    resp = Helper.symbol_info(v["option_exchange"], result["symbol"])
    return resp


def create_strategies(SYMBOLS_TO_TRADE):
    strategies = []
    for k, v in SYMBOLS_TO_TRADE.items():
        lst_of_option_type = ["C", "P"]
        for option_type in lst_of_option_type:
            symbol_info = find_trading_symbol_to_trade(option_type, {k: v})
            print(symbol_info)
            timer(5)
            strgy = EnterAndExit(
                symbol=symbol_info["symbol"],
                low=symbol_info["low"],
                ltp=symbol_info["ltp"],
                exchange=v["option_exchange"],
                quantity=v["quantity"],
                target=v["target"],
            )
            strategies.append(strgy)
    return strategies


def main():
    try:
        while not is_time_past(O_SETG["trade"]["start"]):
            print(f"waiting till {O_SETG['trade']['start']}")

        SYMBOLS_TO_TRADE = _init()
        strategies: list[EnterAndExit] = create_strategies(SYMBOLS_TO_TRADE)
        while not is_time_past(O_SETG["trade"]["stop"]):
            for strgy in strategies:
                msg = f"{strgy._symbol} is going to {strgy._fn}"
                resp = strgy.run(Helper.orders, Helper.get_quotes())
                logging.info(f"{msg} returned {resp}")
    except KeyboardInterrupt:
        __import__("sys").exit()
    except Exception as e:
        print_exc()
        logging.error(f"{e} while init")


if __name__ == "__main__":
    main()
