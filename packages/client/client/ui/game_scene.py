from abc import ABC, abstractmethod


class GameScene(ABC):
    def __init__(self, app):
        self.app = app
        self.node = self.app.render.attachNewNode("SceneNode")
        self.ui_elements = []
    
    def setup(self):
        pass
    
    @abstractmethod
    def step(self, dt):
        pass
    
    def cleanup(self):
        for element in self.ui_elements:
            element.destroy()
        self.ui_elements = []
        
        self.node.removeNode()
