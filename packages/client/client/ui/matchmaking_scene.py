from enum import Enum
import sys
from typing import Optional
import time
from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectButton import DirectButton
from direct.gui.OnscreenText import OnscreenText
from direct.task import Task
from panda3d.core import TextNode

from ui.game_scene import GameScene
from core.piece import Color
from controller.network import ServerConnector
from ui.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
)

# Import deferred to avoid circular import
# from ui.online_pvp_match_scene import OnlinePvPMatchScene


class MatchmakingScene(GameScene):
    def __init__(self, base: ShowBase, connector: ServerConnector):
        super().__init__(base)

        self.app = base
        self.connector = connector
        self.state = "connecting"
        self.message = "Connecting to server..."
        self.match_id = None
        self.opponent = None
        self.opponent_ready = False
        self.start_time = time.time()
        self.next_scene = None

        # Set up callbacks
        self.connector.set_connected_callback(self.on_connected)
        self.connector.set_error_callback(self.on_error)
        self.connector.set_queued_callback(self.on_queued)
        self.connector.set_queue_cancelled_callback(self.on_queue_cancelled)
        self.connector.set_match_found_callback(self.on_match_found)
        self.connector.set_ready_confirmed_callback(self.on_ready_confirmed)
        self.connector.set_opponent_ready_callback(self.on_opponent_ready)
        self.connector.set_match_started_callback(self.on_match_started)
        self.connector.set_match_cancelled_callback(self.on_match_cancelled)

    def setup(self):
        self.app.setBackgroundColor(0.94, 0.94, 0.94)  # Light gray background

        # Set up camera
        self.app.disableMouse()
        self.app.camera.setPos(0, -10, 0)
        self.app.camera.lookAt(0, 0, 0)

        # Create UI elements
        self.create_ui()

        # Set up key handlers
        self.setup_input()

        # Add task to update matchmaking state
        self.app.taskMgr.add(self.step, "MatchmakingStepTask")

    def create_ui(self):
        # Title text
        self.title_text = OnscreenText(
            text="Animal Chess Matchmaking",
            pos=(0, 0.7),
            scale=0.1,
            fg=(0, 0, 0, 1),
            align=TextNode.ACenter,
        )

        # Status message
        self.status_text = OnscreenText(
            text=self.message,
            pos=(0, 0.5),
            scale=0.05,
            fg=(0, 0, 0, 1),
            align=TextNode.ACenter,
        )

        # Search time or match info
        self.info_text = OnscreenText(
            text="",
            pos=(0, 0.4),
            scale=0.04,
            fg=(0.4, 0.4, 0.4, 1),
            align=TextNode.ACenter,
        )

        # Ready status
        self.ready_status_text = OnscreenText(
            text="",
            pos=(0, 0.3),
            scale=0.04,
            fg=(0.4, 0.4, 0.4, 1),
            align=TextNode.ACenter,
        )

        # Help text
        self.help_text = OnscreenText(
            text="",
            pos=(0, -0.7),
            scale=0.04,
            fg=(0.4, 0.4, 0.4, 1),
            align=TextNode.ACenter,
        )

        # Quit button
        self.quit_button = DirectButton(
            text="QUIT",
            scale=0.07,
            pos=(0.9, 0, 0.9),
            frameColor=(0.8, 0.2, 0.2, 1),
            command=self.quit_game,
        )

        # Menu button
        self.menu_button = DirectButton(
            text="MENU",
            scale=0.07,
            pos=(0.7, 0, 0.9),
            frameColor=(0.3, 0.3, 0.8, 1),
            command=self.return_to_menu,
        )

    def setup_input(self):
        self.app.accept("space", self.on_space_pressed)
        self.app.accept("escape", self.on_escape_pressed)

    def update_ui(self):
        # Update status text
        self.status_text.setText(self.message)

        # Update info text based on state
        if self.state == "searching":
            elapsed = int(time.time() - self.start_time)
            self.info_text.setText(f"Searching for {elapsed}s... (Press ESC to cancel)")
        elif self.state in ["match_found", "ready"]:
            self.info_text.setText(f"Match ID: {self.match_id}")
        else:
            self.info_text.setText("")

        # Update ready status
        if self.state in ["match_found", "ready"]:
            ready_status = "You: "
            ready_status += "Ready ✓" if self.state == "ready" else "Not Ready ✗"
            ready_status += " | Opponent: "
            ready_status += "Ready ✓" if self.opponent_ready else "Not Ready ✗"
            self.ready_status_text.setText(ready_status)
        else:
            self.ready_status_text.setText("")

        # Update help text
        if self.state == "idle":
            self.help_text.setText("Press SPACE to find a match")
        elif self.state == "searching":
            self.help_text.setText("Press ESC to cancel search")
        elif self.state == "match_found":
            self.help_text.setText("Press SPACE to ready up or ESC to cancel")
        elif self.state == "ready":
            self.help_text.setText("Press ESC to cancel")
        else:
            self.help_text.setText("")

    def on_space_pressed(self):
        if self.state == "idle":
            self.connector.find_game()
        elif self.state == "match_found":
            self.connector.start_game(self.match_id)

    def on_escape_pressed(self):
        if self.state == "searching":
            self.connector.cancel_find_game()
        elif self.state in ["match_found", "ready"]:
            self.connector.cancel_start_game(self.match_id)
        else:
            self.return_to_menu()

    def on_connected(self, message: str):
        self.state = "idle"
        self.message = "Connected! Press SPACE to search for a match."
        self.update_ui()

    def on_error(self, message: str):
        self.message = f"Error: {message}"
        self.update_ui()

    def on_queued(self, message: str):
        self.state = "searching"
        self.message = message
        self.start_time = time.time()
        self.update_ui()

    def on_queue_cancelled(self, message: str):
        self.state = "idle"
        self.message = message
        self.update_ui()

    def on_match_found(self, match_id: str, opponent: str):
        self.state = "match_found"
        self.match_id = match_id
        self.opponent = opponent
        self.message = f"Match found! Opponent: {opponent}. Press SPACE to ready up."
        self.update_ui()

    def on_ready_confirmed(self, match_id: str):
        self.state = "ready"
        self.message = "Ready! Waiting for opponent..."
        self.update_ui()

    def on_opponent_ready(self, match_id: str):
        self.opponent_ready = True
        if self.state == "match_found":
            self.message = f"Opponent is ready! Press SPACE to ready up."
        elif self.state == "ready":
            self.message = "Both players ready. Starting game..."
        self.update_ui()

    def on_match_started(self, match_id: str, color: Color):
        self.message = "Match starting..."
        self.update_ui()

        from ui.online_pvp_match_scene import OnlinePvPMatchScene

        self.next_scene = OnlinePvPMatchScene(
            self.app, self.connector, match_id, self.opponent, color
        )

    def on_match_cancelled(self, match_id: str, reason: str):
        self.state = "idle"
        self.match_id = None
        self.opponent = None
        self.opponent_ready = False
        self.message = f"Match cancelled: {reason}. Press SPACE to search again."
        self.update_ui()

    def quit_game(self):
        self.connector.Disconnect()
        sys.exit()

    def return_to_menu(self):
        from ui.menu_scene import MenuScene

        self.cleanup()
        self.connector.Disconnect()
        self.next_scene = MenuScene(self.app)

    def step(self, dt):
        self.connector.Pump()

        if self.state == "searching":
            self.update_ui()

        if self.next_scene:
            return self.next_scene

    def cleanup(self):
        self.title_text.destroy()
        self.status_text.destroy()
        self.info_text.destroy()
        self.ready_status_text.destroy()
        self.help_text.destroy()
        self.quit_button.destroy()
        self.menu_button.destroy()

        # Remove key handlers
        self.app.ignore("space")
        self.app.ignore("escape")

        # Remove task
        self.app.taskMgr.remove("MatchmakingStepTask")
