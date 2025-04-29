from PodSixNet.Connection import ConnectionListener, connection
from PodSixNet.EndPoint import EndPoint
from core.piece import Color, Piece
from core.map import Position
from typing import Callable, Optional


class ServerConnector(ConnectionListener):
    __connection: EndPoint

    __move_made_callback: Optional[Callable[[Piece, Position, str], None]]

    def __init__(self, *, ip: str, port: int):
        super().__init__()
        self.__connection = connection
        connection.DoConnect((ip, port))
        self.__match_found_callback = None
        self.__match_started_callback = None
        self.__opponent_ready_callback = None
        self.__match_cancelled_callback = None
        self.__move_made_callback = None
        self.__game_over_callback = None
        self.__connected_callback = None
        self.__error_callback = None
        self.__queued_callback = None
        self.__queue_cancelled_callback = None
        self.__ready_confirmed_callback = None

    def Network_error(self, data):
        if self.__error_callback:
            self.__error_callback(data.get("message", "Unknown error"))

    def Network_connected(self, data):
        if self.__connected_callback:
            self.__connected_callback(data.get("message", "Connected to server"))

    def Network_queued(self, data):
        if self.__queued_callback:
            self.__queued_callback(data.get("message", "Looking for opponent"))

    def Network_queue_cancelled(self, data):
        if self.__queue_cancelled_callback:
            self.__queue_cancelled_callback(data.get("message", "Search cancelled"))

    def Network_match_found(self, data):
        if self.__match_found_callback:
            match_id = data.get("match_id")
            opponent = data.get("opponent")
            self.__match_found_callback(match_id, opponent)

    def Network_ready_confirmed(self, data):
        if self.__ready_confirmed_callback:
            match_id = data.get("match_id")
            self.__ready_confirmed_callback(match_id)

    def Network_opponent_ready(self, data):
        if self.__opponent_ready_callback:
            match_id = data.get("match_id")
            self.__opponent_ready_callback(match_id)

    def Network_match_started(self, data):
        if self.__match_started_callback:
            match_id = data.get("match_id")
            color = data.get("color")
            color = Color.RED if color == "red" else Color.BLUE
            self.__match_started_callback(match_id, color)

    def Network_match_cancelled(self, data):
        if self.__match_cancelled_callback:
            match_id = data.get("match_id")
            reason = data.get("reason", "unknown")
            self.__match_cancelled_callback(match_id, reason)

    def Network_move_made(self, data):
        if self.__move_made_callback:
            piece_data = data.get("piece")
            position_data = data.get("position")
            player = data.get("player")

            if piece_data is None or position_data is None or player is None:
                if self.__error_callback:
                    self.__error_callback("Missing move data from server.")
                return
            piece = Piece.Schema().load(piece_data)
            position = Position.Schema().load(position_data)

            self.__move_made_callback(piece, position, player)

    def Network_game_over(self, data):
        if self.__game_over_callback:
            winner = data.get("winner")
            reason = data.get("reason")
            self.__game_over_callback(winner, reason)

    def Disconnect(self):
        self.__connection.Close()

    def Send(self, data):
        self.__connection.Send(data)

    def Pump(self):
        super().Pump()
        connection.Pump()

    def find_game(self):
        self.Send({"action": "find_game"})

    def cancel_find_game(self):
        self.Send({"action": "cancel_find_game"})

    def start_game(self, match_id: str):
        self.Send({"action": "start_game", "match_id": match_id})

    def cancel_start_game(self, match_id: str):
        self.Send({"action": "cancel_start_game", "match_id": match_id})

    def move(self, piece: Piece, position: Position):
        self.Send(
            {
                "action": "move",
                "piece": Piece.Schema().dump(piece),
                "position": Position.Schema().dump(position),
            }
        )

    def concede(self):
        self.Send({"action": "concede"})

    def set_connected_callback(self, callback: Callable[[str], None]):
        self.__connected_callback = callback

    def set_error_callback(self, callback: Callable[[str], None]):
        self.__error_callback = callback

    def set_queued_callback(self, callback: Callable[[str], None]):
        self.__queued_callback = callback

    def set_queue_cancelled_callback(self, callback: Callable[[str], None]):
        self.__queue_cancelled_callback = callback

    def set_match_found_callback(self, callback: Callable[[str, str], None]):
        self.__match_found_callback = callback

    def set_ready_confirmed_callback(self, callback: Callable[[str], None]):
        self.__ready_confirmed_callback = callback

    def set_opponent_ready_callback(self, callback: Callable[[str], None]):
        self.__opponent_ready_callback = callback

    def set_match_started_callback(self, callback: Callable[[str, Color], None]):
        self.__match_started_callback = callback

    def set_match_cancelled_callback(self, callback: Callable[[str, str], None]):
        self.__match_cancelled_callback = callback

    def set_move_made_callback(self, callback: Callable[[Piece, Position, str], None]):
        self.__move_made_callback = callback

    def set_game_over_callback(self, callback: Callable[[str, str], None]):
        self.__game_over_callback = callback
