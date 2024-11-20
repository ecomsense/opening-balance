import time
from constants import logging


class Wserver:
    # flag to tell us if the websocket is open
    socket_opened = False
    ltp = {}

    def __init__(self, broker, tokens):
        self.api = broker.finvasia
        self.tokens = tokens
        ret = self.api.start_websocket(
            order_update_callback=self.event_handler_order_update,
            subscribe_callback=self.event_handler_quote_update,
            socket_open_callback=self.open_callback,
        )
        if ret:
            logging.debug(f"{ret} ws started")

    def open_callback(self):
        self.socket_opened = True
        print("websocket is connected")
        self.api.subscribe(self.tokens, feed_type="d")
        # api.subscribe(['NSE|22', 'BSE|522032'])

    # application callbacks
    def event_handler_order_update(self, message):
        logging.info("order event: " + str(message))

    def event_handler_quote_update(self, message):
        # e   Exchange
        # tk  Token
        # lp  LTP
        # pc  Percentage change
        # v   volume
        # o   Open price
        # h   High price
        # l   Low price
        # c   Close price
        # ap  Average trade price
        logging.debug(
            "quote event: {0}".format(time.strftime("%d-%m-%Y %H:%M:%S")) + str(message)
        )
        val = message.get("lp", False)
        if val:
            self.ltp[message["e"] + "|" + message["tk"]] = val
        """
        if self.tokens:
            self.api.subscribe(self.tokens, feed_type="d")
        """


if __name__ == "__main__":
    from helper import Helper

    token = ["NSE|22", "NSE|34"]
    wserver = Wserver(Helper.api, token)
    while True:
        print(wserver.ltp)
        time.sleep(1)
        # wserver.tokens = ["NSE:25"]
