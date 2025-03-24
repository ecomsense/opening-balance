import random
from functools import wraps
from traceback import print_exc

import pendulum as plum

from constants import O_FUTL, S_DATA


def dict_from_yml(key_to_search, value_to_match):
    try:
        dct = {}
        sym_from_yml = O_FUTL.get_lst_fm_yml(S_DATA + "symbols.yml")
        for _, dct in sym_from_yml.items():
            if isinstance(dct, dict) and dct[key_to_search] == value_to_match:
                return dct
        print(f"{dct=}")
        return dct
    except Exception as e:
        print(f"dict from yml error: {e}")
        print_exc()


def retry_until_not_none(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = None
        while result is None:
            result = func(*args, **kwargs)
            if result is None:
                print("WAITING FOR LTP")
        return result

    return wrapper


def generate_unique_id():
    # Get the current timestamp
    timestamp = plum.now().format("YYYYMMDDHHmmssSSS")

    # Generate a random 6-digit number
    random_num = random.randint(100000, 999999)

    # Combine timestamp and random number into a single integer
    unique_id = int(f"{timestamp}{random_num}")
    return unique_id
