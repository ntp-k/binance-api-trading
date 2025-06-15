import subprocess
import os

subprocess.run(
    f'PYTHONPATH="{os.path.dirname(os.path.abspath(__file__))}"',
    shell=True
)

from core.bot_manager import BotManager
if __name__ == "__main__":
    bot_manager = BotManager()
    bot_manager.load_bot_configs()
    bot_manager.init_bots()


