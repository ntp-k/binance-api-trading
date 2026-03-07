import sys
from typing import List, Optional

from core.bot_manager import BotManager
from commons.custom_logger import CustomLogger


def parse_arguments() -> Optional[List[str]]:
    """
    Parse command line arguments for bot IDs.
    
    Returns:
        List of bot IDs if specified, None to run all bots
        
    Examples:
        python3 main.py          -> None (run all enabled bots)
        python3 main.py 25       -> ['25']
        python3 main.py aa bb    -> ['aa', 'bb']
    """
    if len(sys.argv) > 1:
        return sys.argv[1:]
    return None


def main():
    logger = CustomLogger(name='main')
    
    # Parse command line arguments
    bot_ids = parse_arguments()
    
    if bot_ids:
        logger.info(message=f'🚀  Starting Trading Bot(s): {", ".join(bot_ids)} 🤖...')
    else:
        logger.info(message='🚀  Starting All Enabled Trading Bots 🤖...')
    
    # Initialize and run bot manager
    bot_manager = BotManager(bot_ids=bot_ids)
    bot_manager.run()
    
    logger.info(message='👋  See you next time!')


if __name__ == '__main__':
    main()

# EOF
