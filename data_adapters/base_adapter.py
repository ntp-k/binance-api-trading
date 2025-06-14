from abc import ABC, abstractmethod

class BaseAdapter(ABC):
    @abstractmethod
    def fetch_bot_configs(self):
        pass