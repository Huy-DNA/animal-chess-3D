from typing import List, Optional, Tuple
from marshmallow_dataclass import dataclass
from core.piece import Color


@dataclass(frozen=True)
class Location:
    is_river: bool
    cave_color: Optional[Color]
    trap_color: Optional[Color]


@dataclass(frozen=True)
class Position:
    x: int
    y: int

    def is_left(self, position) -> bool:
        return self.x == position.x - 1 and self.y == position.y

    def is_right(self, position) -> bool:
        return self.x == position.x + 1 and self.y == position.y

    def is_up(self, position) -> bool:
        return self.y == position.y - 1 and self.x == position.x

    def is_down(self, position) -> bool:
        return self.y == position.y + 1 and self.x == position.x


@dataclass(frozen=True)
class Cell:
    location: Location
    position: Position


@dataclass(frozen=True)
class Map:
    locations: List[List[Location]]

    def width(self) -> int:
        return len(self.locations[0])

    def height(self) -> int:
        return len(self.locations)

    def __getitem__(self, indices: Tuple[int, int]) -> Optional[Location]:
        if indices[0] >= self.height() or indices[0] < 0:
            return None
        if indices[1] >= self.width() or indices[1] < 0:
            return None
        return self.locations[indices[0]][indices[1]]

    def get_adjacent_cells(self, pos: Position) -> List[Cell]:
        res = []
        left = self.get_left_cell(pos)
        if left:
            res.append(left)
        right = self.get_right_cell(pos)
        if right:
            res.append(right)
        up = self.get_up_cell(pos)
        if up:
            res.append(up)
        down = self.get_down_cell(pos)
        if down:
            res.append(down)
        return res

    def get_adjacent_non_river_cells(self, pos: Position) -> List[Cell]:
        res = []
        left = self.get_non_river_down_cell(pos)
        if left:
            res.append(left)
        right = self.get_non_river_right_cell(pos)
        if right:
            res.append(right)
        up = self.get_non_river_up_cell(pos)
        if up:
            res.append(up)
        down = self.get_non_river_down_cell(pos)
        if down:
            res.append(down)
        return res

    def get_left_cell(self, pos: Position) -> Optional[Cell]:
        loc = self[pos.y, pos.x - 1]
        if loc is None:
            return None
        return Cell(loc, Position(pos.x - 1, pos.y))

    def get_right_cell(self, pos: Position) -> Optional[Cell]:
        loc = self[pos.y, pos.x + 1]
        if loc is None:
            return None
        return Cell(loc, Position(pos.x + 1, pos.y))

    def get_up_cell(self, pos: Position) -> Optional[Cell]:
        loc = self[pos.y - 1, pos.x]
        if loc is None:
            return None
        return Cell(loc, Position(pos.x, pos.y - 1))

    def get_down_cell(self, pos: Position) -> Optional[Cell]:
        loc = self[pos.y + 1, pos.x]
        if loc is None:
            return None
        return Cell(loc, Position(pos.x, pos.y + 1))

    def get_non_river_left_cell(self, pos: Position) -> Optional[Cell]:
        pos = Position(pos.x - 1, pos.y)
        loc = self[pos.y, pos.x]
        while loc is not None and loc.is_river:
            pos = Position(pos.x - 1, pos.y)
            loc = self[pos.y, pos.x]
        if loc is None:
            return None
        return Cell(loc, pos)

    def get_non_river_right_cell(self, pos: Position) -> Optional[Cell]:
        pos = Position(pos.x + 1, pos.y)
        loc = self[pos.y, pos.x]
        while loc is not None and loc.is_river:
            pos = Position(pos.x + 1, pos.y)
            loc = self[pos.y, pos.x]
        if loc is None:
            return None
        return Cell(loc, pos)

    def get_non_river_up_cell(self, pos: Position) -> Optional[Cell]:
        pos = Position(pos.x, pos.y - 1)
        loc = self[pos.y, pos.x]
        while loc is not None and loc.is_river:
            pos = Position(pos.x, pos.y - 1)
            loc = self[pos.y, pos.x]
        if loc is None:
            return None
        return Cell(loc, pos)

    def get_non_river_down_cell(self, pos: Position) -> Optional[Cell]:
        pos = Position(pos.x, pos.y + 1)
        loc = self[pos.y, pos.x]
        while loc is not None and loc.is_river:
            pos = Position(pos.x, pos.y + 1)
            loc = self[pos.y, pos.x]
        if loc is None:
            return None
        return Cell(loc, pos)


DEFAULT_MAP = Map(
    [
        [
            Location(False, None, None),
            Location(False, None, None),
            Location(False, None, Color.RED),
            Location(False, Color.RED, None),
            Location(False, None, Color.RED),
            Location(False, None, None),
            Location(False, None, None),
        ],
        [
            Location(False, None, None),
            Location(False, None, None),
            Location(False, None, None),
            Location(False, None, Color.RED),
            Location(False, None, None),
            Location(False, None, None),
            Location(False, None, None),
        ],
        [
            Location(False, None, None),
            Location(False, None, None),
            Location(False, None, None),
            Location(False, None, None),
            Location(False, None, None),
            Location(False, None, None),
            Location(False, None, None),
        ],
        [
            Location(False, None, None),
            Location(True, None, None),
            Location(True, None, None),
            Location(False, None, None),
            Location(True, None, None),
            Location(True, None, None),
            Location(False, None, None),
        ],
        [
            Location(False, None, None),
            Location(True, None, None),
            Location(True, None, None),
            Location(False, None, None),
            Location(True, None, None),
            Location(True, None, None),
            Location(False, None, None),
        ],
        [
            Location(False, None, None),
            Location(True, None, None),
            Location(True, None, None),
            Location(False, None, None),
            Location(True, None, None),
            Location(True, None, None),
            Location(False, None, None),
        ],
        [
            Location(False, None, None),
            Location(False, None, None),
            Location(False, None, None),
            Location(False, None, None),
            Location(False, None, None),
            Location(False, None, None),
            Location(False, None, None),
        ],
        [
            Location(False, None, None),
            Location(False, None, None),
            Location(False, None, None),
            Location(False, None, Color.BLUE),
            Location(False, None, None),
            Location(False, None, None),
            Location(False, None, None),
        ],
        [
            Location(False, None, None),
            Location(False, None, None),
            Location(False, None, Color.BLUE),
            Location(False, Color.BLUE, None),
            Location(False, None, Color.BLUE),
            Location(False, None, None),
            Location(False, None, None),
        ],
    ]
)
