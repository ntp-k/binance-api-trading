import json

from models.bot_config import BotConfig

def load_config(file_path: str) -> list[BotConfig]:
    with open(file=file_path, mode="r", encoding="utf-8") as f:
        raw = json.load(fp=f)
    return [BotConfig.from_dict(data=item) for item in raw]

# EOF
