from direct.task.Task import Task
from ui.menu_scene import MenuScene
from ui.constants import SCREEN_WIDTH, SCREEN_HEIGHT

from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties


class GameLoop(ShowBase):
    def __init__(self):
        super().__init__()

        props = WindowProperties()
        props.setSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        props.setTitle("Game Title")
        self.win.requestProperties(props)

        self.disableMouse()
        self.setFrameRateMeter(True)

        globalClock.setMode(globalClock.MLimited)
        globalClock.setFrameRate(60)

        self.current_scene = None
        self.next_scene = None

        self.switch_scene(MenuScene(self))

        self.taskMgr.add(self.game_loop, "GameLoop")

        self.accept("escape", self.user_exit)
        self.accept("window-close", self.user_exit)

    def switch_scene(self, scene):
        if self.current_scene:
            self.current_scene.cleanup()

        self.current_scene = scene
        self.next_scene = None

        self.current_scene.setup()

    def game_loop(self, task):
        if not self.current_scene:
            return Task.cont

        if self.next_scene:
            self.switch_scene(self.next_scene)
            return Task.cont

        result = self.current_scene.step(self.clock.getDt())

        if result:
            self.next_scene = result

        return Task.cont

    def user_exit(self):
        self.userExit()
