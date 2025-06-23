import subprocess
import os
import argparse
from dotenv import load_dotenv

subprocess.run(
    f'PYTHONPATH="{os.path.dirname(os.path.abspath(__file__))}"',
    shell=True
)

from models.enum.run_mode import RunMode
from core.bot_manager import BotManager
from commons.custom_logger import CustomLogger

load_dotenv()


def main(run_mode, offline):

    logger = CustomLogger('main')
    logger.info('🚀  Starting Binance Trading Bot 🤖...')

    run_mode = RunMode(run_mode.upper())
    logger.info(f"🔄  Running mode: {run_mode.value}")
    logger.info(f"🔄  Running offline: {offline}")

    bot_manager = BotManager(run_mode=run_mode, is_offline=offline)
    bot_manager.init_bots()

    bot_manager.run_bots()

    logger.info(f'👋  See you next time!')
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run bot with specified mode.')
    parser.add_argument(
        "-r", "--run-mode",
        choices=["backtest", "forwardtest", "live"],
        default="backtest",
        help="Mode to run the bot (default: backtest)"
    )
    
    parser.add_argument(
        "-o", "--offline",
        action="store_true",
        help="Run in offline mode (default: True)"
    )
    args = parser.parse_args()

    main(args.run_mode, args.offline)



# EOF
