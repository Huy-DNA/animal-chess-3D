from dotenv import load_dotenv
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode, LVecBase4f

from ui.button import Button
from ui.difficulty_menu_scene import DifficultyMenuScene
from ui.offline_pvp_match_scene import OfflinePvPMatchScene
from ui.game_scene import GameScene
from ui.constants import SCREEN_WIDTH, SCREEN_HEIGHT

load_dotenv()


class MenuScene(GameScene):
    def __init__(self, app):
        super().__init__(app)

        self.title = None
        self.buttons = []
        self.next_scene = None

    def setup(self):
        background_color = LVecBase4f(0.2, 0.4, 0.2, 1.0)
        self.app.win.setClearColor(background_color)

        self.title = OnscreenText(
            text="Animal Chess",
            pos=(0, 0.7),
            scale=0.15,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter,
            mayChange=False,
        )
        self.ui_elements.append(self.title)

        button_width = 400
        button_height = 300
        button_spacing = -100
        start_y = SCREEN_HEIGHT // 2 - 200

        buttons_info = [
            "Computer vs Player",
            "Player vs Player",
            "Quit",
        ]

        self.buttons = []
        for i, text in enumerate(buttons_info):
            x = SCREEN_WIDTH // 2 - button_width // 2
            y = start_y + i * (button_height + button_spacing)
            button = Button(x, y, button_width, button_height, text, 36)
            self.buttons.append(button)
            self.ui_elements.append(button)

        self.buttons[0].set_click_callback(lambda pos: self.handle_button_click(0))
        self.buttons[1].set_click_callback(lambda pos: self.handle_button_click(1))
        self.buttons[2].set_click_callback(lambda pos: self.handle_button_click(2))

    def handle_button_click(self, button_index: int):
        if button_index == 0:
            self.next_scene = DifficultyMenuScene(self.app)
        elif button_index == 1:
            self.next_scene = OfflinePvPMatchScene(self.app)
        elif button_index == 2:
            self.app.userExit()

    def step(self, dt):
        return self.next_scene
