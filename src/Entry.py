from constants import O_SETG
# pprint is optional .. it pretty prints
# complex data types
from pprint import pprint

pprint(O_SETG)
keys = ["log", "targets", "trade", "MCX"]
four_key_items = {key: value for key, value in O_SETG.items() if isinstance(value, dict) and key not in keys}
print(f"{four_key_items=}")
