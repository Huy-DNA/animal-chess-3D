from marshmallow_dataclass import dataclass
from enum import Enum


class PieceType(Enum):
    MOUSE = 0
    CAT = 1
    WOLF = 2
    DOG = 3
    LEOPARD = 4
    TIGER = 5
    LION = 6
    ELEPHANT = 7

    def to_string(self) -> str:
        if self == PieceType.MOUSE:
            return "mouse"
        elif self == PieceType.CAT:
            return "cat"
        elif self == PieceType.WOLF:
            return "wolf"
        elif self == PieceType.DOG:
            return "dog"
        elif self == PieceType.LEOPARD:
            return "leopard"
        elif self == PieceType.TIGER:
            return "tiger"
        elif self == PieceType.LION:
            return "lion"
        elif self == PieceType.ELEPHANT:
            return "elephant"
        raise RuntimeError("Unreachable")

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

class Color(Enum):
    RED = 0
    BLUE = 1

    def to_string(self) -> str:
        return "red" if self == Color.RED else "blue"


@dataclass(frozen=True)
class Piece:
    color: Color
    type: PieceType

    def can_cross_river(self) -> bool:
        return self.type == PieceType.MOUSE

    def can_jump_river(self) -> bool:
        return self.type == PieceType.LION or self.type == PieceType.TIGER

    def get_default_level(self) -> int:
        return self.type
