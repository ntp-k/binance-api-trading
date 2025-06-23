from abc import ABC, abstractmethod

class BaseAdapter(ABC):

    def __init__(self) -> None:
        super().__init__()

    def fetch_activate_bots(self):
        pass

    def fetch_bot(self):
        pass

    def create_run(self):
        pass

# EOF
