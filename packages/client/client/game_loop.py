import pygame
from pygame.time import Clock
from ui.menu_scene import MenuScene
from ui.game_scene import GameScene
from ui.constants import SCREEN_WIDTH, SCREEN_HEIGHT


class GameLoop:
    __screen: pygame.Surface
    __running: bool
    __fps: int
    __clock: Clock
    __current_scene: GameScene

    def __init__(self):
        pygame.init()
        self.__screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.__running = False
        self.__fps = 60
        self.__clock = pygame.time.Clock()
        self.__switch_scene(MenuScene(self.__screen))

    def __switch_scene(self, scene: GameScene):
        self.__current_scene = scene

    def run(self):
        self.__running = True

        while self.__running:
            scene_events = []
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.__running = False
                    break

                scene_events.append(event)

            next_scene = self.__current_scene.step(scene_events)
            if next_scene:
                self.__switch_scene(next_scene)
            pygame.display.flip()

            self.__clock.tick(self.__fps)

        pygame.quit()
