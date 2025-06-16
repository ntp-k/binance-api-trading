import subprocess
import os

subprocess.run(
    f'PYTHONPATH="{os.path.dirname(os.path.abspath(__file__))}"',
    shell=True
)

from core.bot_manager import BotManager
from commons.custom_logger import CustomLogger


if __name__ == "__main__":
    logger = CustomLogger('main')
    logger.info('Starting Binance Trading Bot...')
    bot_manager = BotManager()
    bot_manager.load_bot_configs()
    bot_manager.init_bots()
    bot_manager.run_bots()

# EOF
