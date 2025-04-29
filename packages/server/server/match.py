from core.game import Game
from core.map import Color, dataclass
from server_types import MatchId, Addr


@dataclass
class Match:
    id: MatchId
    game: Game
    red_player: Addr
    blue_player: Addr
    turn: Color = Color.RED

    def get_players(self) -> Addr:
        return [self.red_player, self.blue_player]
