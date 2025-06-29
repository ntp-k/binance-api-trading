from dataclasses import dataclass

from models.enum.position_side import PositionSide

@dataclass
class PositionSignal:
    position_side: PositionSide
    reason: str

# EOF
