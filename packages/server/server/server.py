from core.game import Game
from core.piece import Color, Piece
from core.map import Position
from typing import Any, Dict, Optional, Set
from PodSixNet.Channel import Channel
from PodSixNet.Server import Server
from queue import Queue
import uuid
import match
from server_types import Addr, MatchId


class ClientChannel(Channel):
    _server: "GameServer"

    def Network_move(self, data):
        piece: Piece
        pos: Position
        try:
            piece = Piece.Schema().load(data["piece"])
            pos = Position.Schema().load(data["position"])
        except Exception:
            self.Send({"action": "error", "message": "Invalid payload"})
            return

        if self.addr not in self._server.get_client_matches():
            self.Send({"action": "error", "message": "Not in a match"})
            return

        match_id = self._server.get_client_matches()[self.addr]
        match = self._server.get_matches().get(match_id)

        if not match:
            self.Send({"action": "error", "message": "Match not found"})
            return

        success = match.game.move(piece, pos)
        if not success:
            self.Send({"action": "error", "message": "Invalid move"})
            return

        for player_addr in match.get_players():
            if player_addr in self._server.get_registered_clients():
                self._server.get_registered_clients()[player_addr].Send(
                    {
                        "action": "move_made",
                        "piece": Piece.Schema().dump(piece),
                        "position": Position.Schema().dump(pos),
                        "player": str(self.addr),
                    }
                )

    def Network_find_game(self, data):
        if self.addr in self._server.get_client_matches():
            self.Send({"action": "error", "message": "Already in a match"})
            return

        if self.addr in self._server.get_pending_clients_list():
            self.Send({"action": "error", "message": "Already in queue"})
            return

        self._server.add_to_pending_queue(self.addr)
        self.Send({"action": "queued", "message": "Looking for opponent"})

        self._server.try_match_clients()

    def Network_cancel_find_game(self, data):
        if self._server.remove_from_pending_queue(self.addr):
            self.Send({"action": "queue_cancelled", "message": "Search cancelled"})
        else:
            self.Send({"action": "error", "message": "Not in queue"})

    def Network_start_game(self, data):
        try:
            match_id_str = data.get("match_id")
            if not match_id_str:
                self.Send({"action": "error", "message": "Match ID required"})
                return

            match_id = MatchId(match_id_str)

            if not self._server.is_pending_match_player(self.addr, match_id):
                self.Send(
                    {"action": "error", "message": "Not part of this pending match"}
                )
                return

            self._server.set_player_ready(self.addr, match_id)
            self.Send({"action": "ready_confirmed", "match_id": match_id_str})

            if self._server.are_all_players_ready(match_id):
                self._server.start_pending_match(match_id)
        except Exception as e:
            self.Send({"action": "error", "message": f"Failed to start game: {str(e)}"})

    def Network_cancel_start_game(self, data):
        try:
            match_id_str = data.get("match_id")
            if not match_id_str:
                self.Send({"action": "error", "message": "Match ID required"})
                return

            match_id = MatchId(match_id_str)

            if self._server.cancel_pending_match(match_id, self.addr):
                self.Send({"action": "match_cancelled", "match_id": match_id_str})
            else:
                self.Send({"action": "error", "message": "Could not cancel match"})
        except Exception:
            self.Send({"action": "error", "message": "Invalid match ID"})

    def Network_concede(self, data):
        if self.addr not in self._server.get_client_matches():
            self.Send({"action": "error", "message": "Not in a match"})
            return

        match_id = self._server.get_client_matches()[self.addr]
        match = self._server.get_matches().get(match_id)

        if not match:
            self.Send({"action": "error", "message": "Match not found"})
            return

        winner = match.concede(self.addr)

        for player_addr in match.get_players():
            if player_addr in self._server.get_registered_clients():
                self._server.get_registered_clients()[player_addr].Send(
                    {"action": "game_over", "winner": str(winner), "reason": "concede"}
                )

        self._server.end_match(match_id)

    def handle_close(self):
        super().handle_close()

        if self.addr in self._server.get_client_matches():
            match_id = self._server.get_client_matches()[self.addr]
            match = self._server.get_matches().get(match_id)

            if match:
                for player_addr in match.get_players():
                    if (
                        player_addr != self.addr
                        and player_addr in self._server.get_registered_clients()
                    ):
                        self._server.get_registered_clients()[player_addr].Send(
                            {
                                "action": "game_over",
                                "winner": str(player_addr),
                                "reason": "disconnect",
                            }
                        )
                        break

                self._server.end_match(match_id)

        self._server.remove_from_pending_queue(self.addr)

        self._server.handle_disconnect_pending_matches(self.addr)

        self._server.remove_client(self.addr)


class GameServer(Server):
    channelClass = ClientChannel
    __registered_clients: Dict[Addr, ClientChannel]
    __matches: Dict[MatchId, match.Match]
    __client_matches: Dict[Addr, MatchId]
    __pending_clients: Queue[Addr]
    __pending_clients_list: Set[Addr]
    __pending_matches: Dict[MatchId, Dict[str, Any]]

    def __init__(self, *, ip: str, port: int, listeners=10):
        print(f"Server listening on {ip}:{port}...")
        super().__init__(localaddr=(ip, port), listeners=listeners)
        self.__registered_clients = {}
        self.__matches = {}
        self.__client_matches = {}
        self.__pending_clients = Queue()
        self.__pending_clients_list = set()
        self.__pending_matches = {}

    def Connected(self, channel: ClientChannel, addr: Addr):
        print(f"Client connected: {addr}")
        channel._server = self
        self.__registered_clients[addr] = channel

        channel.Send({"action": "connected", "message": "Connected to server"})

    def remove_client(self, addr: Addr):
        if addr in self.__registered_clients:
            print(f"Client disconnected: {addr}")
            self.__registered_clients.pop(addr)

    def get_registered_clients(self) -> Dict[Addr, ClientChannel]:
        return self.__registered_clients

    def get_matches(self) -> Dict[MatchId, match.Match]:
        return self.__matches

    def get_client_matches(self) -> Dict[Addr, MatchId]:
        return self.__client_matches

    def get_pending_clients_list(self) -> Set[Addr]:
        return self.__pending_clients_list

    def add_to_pending_queue(self, addr: Addr) -> None:
        self.__pending_clients.put(addr)
        self.__pending_clients_list.add(addr)
        print(f"Client {addr} added to matchmaking queue")

    def remove_from_pending_queue(self, addr: Addr) -> bool:
        if addr in self.__pending_clients_list:
            self.__pending_clients_list.remove(addr)
            print(f"Client {addr} removed from matchmaking queue")
            return True
        return False

    def try_match_clients(self) -> Optional[MatchId]:
        if self.__pending_clients.qsize() < 2:
            return None

        client1 = self.__pending_clients.get()
        if (
            client1 not in self.__pending_clients_list
            or client1 not in self.__registered_clients
        ):
            self.__pending_clients_list.discard(client1)
            return self.try_match_clients()

        client2 = self.__pending_clients.get()
        if (
            client2 not in self.__pending_clients_list
            or client2 not in self.__registered_clients
        ):
            self.__pending_clients_list.discard(client2)
            self.__pending_clients.put(client1)
            return self.try_match_clients()

        match_id = self.create_pending_match(client1, client2)
        if match_id:
            self.__pending_clients_list.discard(client1)
            self.__pending_clients_list.discard(client2)

            self.__registered_clients[client1].Send(
                {
                    "action": "match_found",
                    "match_id": str(match_id),
                    "opponent": str(client2),
                }
            )
            self.__registered_clients[client2].Send(
                {
                    "action": "match_found",
                    "match_id": str(match_id),
                    "opponent": str(client1),
                }
            )

            print(f"Pending match created: {match_id} between {client1} and {client2}")
            return match_id

        return None

    def create_pending_match(self, client1: Addr, client2: Addr) -> Optional[MatchId]:
        try:
            match_id = MatchId(str(uuid.uuid4()))

            self.__pending_matches[match_id] = {
                "players": [client1, client2],
                "ready_players": set(),
            }

            return match_id
        except Exception as e:
            print(f"Error creating pending match: {e}")
            return None

    def is_pending_match_player(self, addr: Addr, match_id: MatchId) -> bool:
        if match_id in self.__pending_matches:
            return addr in self.__pending_matches[match_id]["players"]
        return False

    def set_player_ready(self, addr: Addr, match_id: MatchId) -> None:
        if (
            match_id in self.__pending_matches
            and addr in self.__pending_matches[match_id]["players"]
        ):
            self.__pending_matches[match_id]["ready_players"].add(addr)

            for player in self.__pending_matches[match_id]["players"]:
                if player != addr and player in self.__registered_clients:
                    self.__registered_clients[player].Send(
                        {"action": "opponent_ready", "match_id": str(match_id)}
                    )

    def are_all_players_ready(self, match_id: MatchId) -> bool:
        if match_id in self.__pending_matches:
            pending_match = self.__pending_matches[match_id]
            return len(pending_match["ready_players"]) == len(pending_match["players"])
        return False

    def start_pending_match(self, match_id: MatchId) -> None:
        if match_id in self.__pending_matches:
            pending_match = self.__pending_matches[match_id]
            players = pending_match["players"]

            mat = match.Match(match_id, Game(), *players)

            self.__matches[match_id] = mat

            for player in players:
                self.__client_matches[player] = match_id

            for player in players:
                if player in self.__registered_clients:
                    self.__registered_clients[player].Send(
                        {
                            "action": "match_started",
                            "match_id": str(match_id),
                            "color": Color.RED.to_string()
                            if player == mat.red_player
                            else Color.BLUE.to_string(),
                        }
                    )

            self.__pending_matches.pop(match_id)

            print(f"Match started: {match_id}")

    def cancel_pending_match(self, match_id: MatchId, initiator: Addr) -> bool:
        if match_id in self.__pending_matches:
            pending_match = self.__pending_matches[match_id]

            if initiator in pending_match["players"]:
                for player in pending_match["players"]:
                    if player != initiator and player in self.__registered_clients:
                        self.__registered_clients[player].Send(
                            {
                                "action": "match_cancelled",
                                "match_id": str(match_id),
                                "reason": "opponent_cancelled",
                            }
                        )

                self.__pending_matches.pop(match_id)
                print(f"Pending match cancelled: {match_id}")
                return True

        return False

    def handle_disconnect_pending_matches(self, addr: Addr) -> None:
        matches_to_cancel = []

        for match_id, pending_match in self.__pending_matches.items():
            if addr in pending_match["players"]:
                matches_to_cancel.append(match_id)

        for match_id in matches_to_cancel:
            pending_match = self.__pending_matches[match_id]

            for player in pending_match["players"]:
                if player != addr and player in self.__registered_clients:
                    self.__registered_clients[player].Send(
                        {
                            "action": "match_cancelled",
                            "match_id": str(match_id),
                            "reason": "opponent_disconnected",
                        }
                    )

            self.__pending_matches.pop(match_id)
            print(f"Pending match cancelled due to disconnect: {match_id}")

    def end_match(self, match_id: MatchId) -> None:
        if match_id in self.__matches:
            match = self.__matches[match_id]

            for player_addr in match.get_players():
                if player_addr in self.__client_matches:
                    self.__client_matches.pop(player_addr)

            self.__matches.pop(match_id)
            print(f"Match ended: {match_id}")
