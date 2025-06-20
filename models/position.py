from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from models.enum.positino_side import PositionSide

@dataclass
class Position:
    position_id: Optional[int] = None
    run_id: int = 0
    position_side: PositionSide = PositionSide.LONG
    entry_price: float = 0.0
    open_time: datetime = field(default_factory=datetime.now)
    close_time: Optional[datetime] = None
    close_price: Optional[float] = 0.0
    created_at: Optional[datetime] = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        d = self.__dict__
        d['position_side'] = self.position_side.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Position":
        return cls(**data)

# EOF
