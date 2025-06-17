from commons.custom_logger import CustomLogger

class ForwardtestEngine:
    def __init__(self):
        self.logger = CustomLogger(name=ForwardtestEngine.__name__)
        self.logger.debug('Initializing forwardtest bot engine')


    def run(self, klines, config, strategy, trade_engine):
        pass

# EOF
