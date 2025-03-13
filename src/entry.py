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
