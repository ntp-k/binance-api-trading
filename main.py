from core.bot_manager import BotManager
from commons.custom_logger import CustomLogger

def main():
    logger = CustomLogger(name='main')
    logger.info(message='🚀  Starting Trading Bot 🤖...')
    bot_manager = BotManager()
    bot_manager.run()
    logger.info(message=f'👋  See you next time!')


if __name__ == '__main__':
    main()

# EOF
