import argparse

from core.bot_manager import BotManager
from commons.custom_logger import CustomLogger

def main(offline):
    logger = CustomLogger(name='main')
    logger.info(message='🚀  Starting Trading Bot 🤖...')
    bot_manager = BotManager(offline=offline)
    bot_manager.init_bots()
    logger.info(message=f'👋  See you next time!')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o", "--offline",
        action="store_true",
        help="Run in offline mode",
    )
    args = parser.parse_args()
    offline = args.offline

    main(offline=offline)

# EOF
