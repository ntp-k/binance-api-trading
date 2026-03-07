from threading import Thread
from typing import List, Optional

from commons.constants import BOT_CONFIG_PATH
from commons.custom_logger import CustomLogger
from models.bot_config import BotConfig
import core.bot_config_loader as bot_config_loader
from core.bot import Bot


class BotManager:
    """
    Manages multiple trading bot instances with thread-based execution.
    
    Handles bot initialization and thread management.
    Supports running all bots or specific bots by ID.
    """
    
    def __init__(self, bot_ids: Optional[List[str]] = None, config_dir: str = "config"):
        """
        Initialize BotManager.
        
        Args:
            bot_ids: Optional list of bot IDs to run (e.g., ['25', 'aa'])
                    If None, runs all enabled bots
            config_dir: Directory containing bot config files
        """
        self.logger = CustomLogger(name=self.__class__.__name__)
        self.bot_ids = bot_ids
        self.config_dir = config_dir
        self.bots: List[Bot] = []
        self.threads: List[Thread] = []

    def _load_bots_config(self) -> List[BotConfig]:
        """
        Load bot configurations based on initialization parameters.
        
        Returns:
            List of BotConfig instances
            
        Raises:
            FileNotFoundError: If config files don't exist
            ValueError: If config is invalid
        """
        try:
            if self.bot_ids:
                # Load specific bots by ID
                self.logger.info(message=f"Loading specific bots: {', '.join(self.bot_ids)}")
                return bot_config_loader.load_bot_configs_by_ids(
                    bot_ids=self.bot_ids,
                    config_dir=self.config_dir
                )
            else:
                # Load all enabled bots
                self.logger.info(message="Loading all enabled bots from directory")
                return bot_config_loader.load_all_bot_configs(
                    config_dir=self.config_dir,
                    enabled_only=True
                )
        except FileNotFoundError as e:
            self.logger.error(message=f"Config file(s) not found: {e}")
            raise
        except Exception as e:
            self.logger.error_e(message="Failed to load bot configurations", e=e)
            raise

    def _init_bots(self) -> None:
        """Initialize bot instances from configuration."""
        self.logger.debug(message="Initializing bot(s)...")
        
        try:
            self.bots_config: List[BotConfig] = self._load_bots_config()
        except Exception as e:
            self.logger.error_e(message="Failed to load configurations", e=e)
            return
        
        enabled_count = 0
        failed_count = 0
        
        for bot_config in self.bots_config:
            try:
                # When loading specific bots, respect their enabled status
                # When loading all bots, only enabled ones are loaded
                if self.bot_ids and not bot_config.is_enabled:
                    self.logger.warning(
                        message=f'Bot: {bot_config.bot_name} is disabled but was explicitly requested'
                    )
                    # Still skip disabled bots even if explicitly requested
                    continue
                
                # Validate configuration
                bot_config.validate()
                
                self.logger.info(message=f'Loading 🤖  [{bot_config.bot_name}] ...')
                self.logger.debug(message=f'config: {bot_config}')
                bot = Bot(bot_config=bot_config)
                self.bots.append(bot)
                enabled_count += 1
                
            except ValueError as e:
                self.logger.error(message=f"Invalid config for {bot_config.bot_name}: {e}")
                failed_count += 1
            except Exception as e:
                self.logger.error_e(
                    message=f"Failed to create bot [{bot_config.bot_name}]",
                    e=e
                )
                failed_count += 1
        
        self.logger.info(message=f"Loaded {enabled_count} bot(s), {failed_count} failed")

    def execute(self) -> None:
        """Start all bot threads and wait for completion."""
        if not self.bots:
            self.logger.warning(message="No bots to execute")
            return
        
        self.logger.info(message=f"Starting {len(self.bots)} bot(s)...")
        
        # Start all bot threads
        for bot in self.bots:
            try:
                self.logger.info(message=f'Starting 🤖  [{bot.bot_config.bot_name}] ...')
                thread = Thread(
                    target=bot.run,
                    name=bot.bot_config.bot_name,
                    daemon=False
                )
                thread.start()
                self.threads.append(thread)
                self.logger.debug(message=f"Thread started for 🤖  [{bot.bot_config.bot_name}]")
            except Exception as e:
                self.logger.error_e(
                    message=f"Failed to start thread for [{bot.bot_config.bot_name}]",
                    e=e
                )
        
        # Wait for all threads to complete
        self._wait_for_threads()
        
        self.logger.info(message="All bots completed.")

    def _wait_for_threads(self) -> None:
        """Wait for all bot threads to complete."""
        for thread in self.threads:
            try:
                thread.join()
            except Exception as e:
                self.logger.error_e(
                    message=f"Error waiting for thread [{thread.name}]",
                    e=e
                )

    def run(self) -> None:
        """Main entry point to initialize and run all bots."""
        try:
            self._init_bots()
            
            if not self.bots:
                self.logger.warning(message="No bots initialized, exiting")
                return
            
            self.execute()
            self.logger.info(message=f"Total bots run: {len(self.bots)}")
            
        except KeyboardInterrupt:
            self.logger.info(message="Interrupted by user")
        except Exception as e:
            self.logger.error_e(message="Fatal error in bot manager", e=e)
            raise
        finally:
            self.logger.info(message="Bot manager shutdown complete")

# EOF
