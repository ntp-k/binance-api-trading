from models.bot_config import BotConfig
from models.enum.run_mode import RunMode

class Bot:
    # client: BaseClient
    # strategy: BaseStrategy

    def __init__(self, bot_config: BotConfig):
        self.config: BotConfig = bot_config
    
    def _init_entry_strategy(self, entry_strategy):
        pass

    def _init_exit_strategy(self, exit_strategy):
        pass

    def _init_trade_client(self, run_mode: RunMode):
        pass


    def execute(self):
        pass
        # market_data = self.client.fetch_market()
        # position_data = self.client.fetch_position()
        # processed_data = self.strategy.process(market_data)

        # if self.strategy.should_open(processed_data, position_data):
        #     self.client.trade_buy()
        # elif self.strategy.should_close(processed_data, position_data):
        #     self.client.trade_sell()
        
        # self.client.wait()

    def run(self):
        pass
        # count = 0
        # while True:
        #     try:
        #         print(count)
        #         self.execute()
        #         count += 1
        #     except:
        #         print('Error')
        #         break

# EOF
