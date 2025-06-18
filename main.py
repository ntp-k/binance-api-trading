import sys
from models.enum.run_mode import RunMode
from core.bot_manager import BotManager
from commons.custom_logger import CustomLogger
import subprocess
import os
from dotenv import load_dotenv

subprocess.run(
    f'PYTHONPATH="{os.path.dirname(os.path.abspath(__file__))}"',
    shell=True
)

load_dotenv()

def main(logger: CustomLogger):
    run_mode = None
    run_mode_value = None
    try:
        if len(sys.argv) < 2:
            run_mode_value = os.getenv('RUN_MODE', RunMode.BACKTEST.value)
        else:
            run_mode_value = sys.argv[1].upper()
        run_mode = RunMode(run_mode_value)
        logger.info(f"Run mode set to: {run_mode_value}")
    except ValueError as e:
        logger.error_e(
            f"Invalid run mode: {run_mode_value}. Defaulting to BACKTEST mode.", e)
        run_mode = RunMode.BACKTEST

    logger.info(f"🔄  Starting {run_mode_value} trading bot(s)...")

    bot_manager = BotManager(run_mode=run_mode)
    bot_manager.load_active_bots()
    exit()
    bot_manager.init_bots()
    bot_manager.run_bots()

if __name__ == "__main__":
    logger = CustomLogger('main')
    logger.info('🚀  Starting Binance Trading Bot 🤖...')
    main(logger)
    logger.info(f'👋  See you next time!')
    print()

# EOF
