import time

from commons.custom_logger import CustomLogger

class BotEngineLive:
    def __init__(self):
        self.logger = CustomLogger(name=BotEngineLive.__name__)
        self.logger.debug('Initializing live bot engine')


    def run(self, klines, config, strategy, trade_engine):
        pass
        # while True:
        #     kline = fetch_latest_kline(config["symbol"], config["interval"])
        #     strategy.on_update(kline)

        #     if strategy.should_open():
        #         trade = strategy.open_position(kline)
        #         order = place_order(trade)
        #         adapter.log_trade(order)
        #         adapter.log_position_open(order)

        #     if strategy.should_close():
        #         result = strategy.close_position(kline)
        #         order = place_order(result)
        #         adapter.log_trade(order)
        #         adapter.log_position_close(order)

        #     time.sleep(config.get("poll_interval", 5))
