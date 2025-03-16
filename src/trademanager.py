import pendulum


class TradeManager:
    def __init__(self):
        self.market_open = pendulum.today().at(9, 0, 0)  # Market starts at 9:00 AM
        self.market_close = pendulum.today().at(23, 55, 0)  # Market closes at 3:30 PM
        self.candle_times = self._generate_candle_times()
        self.last_trade_time = pendulum.now("Asia/Kolkata")

    def set_last_trade_time(self, trade_time):
        self.last_trade_time = trade_time

    def _generate_candle_times(self):
        """Generate a list of 3-minute candle close times from market open to close."""
        times = []
        time = self.market_open
        while time < self.market_close:
            time = time.add(minutes=3)
            times.append(time)
        return times

    @property
    def can_trade(self):
        """Finds the index of the candle where the trade happened."""
        index = None
        for i, candle_close in enumerate(self.candle_times):
            if self.candle_times[i - 1] <= self.last_trade_time < candle_close:
                index = i
                break
        if index is None or index >= len(self.candle_times):
            return False

        now = pendulum.now("Asia/Kolkata")
        print(now, "is greater than", self.candle_times[index])

        if now > self.candle_times[index]:
            return True
        else:
            return False


if __name__ == "__main__":
    import time

    mgr = TradeManager()

    while True:
        time.sleep(1)
        print(mgr.can_trade)
