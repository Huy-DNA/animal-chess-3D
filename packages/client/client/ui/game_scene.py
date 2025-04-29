from abc import ABC, abstractmethod
from typing import List, Optional
from pygame.event import Event


class GameScene(ABC):
    @abstractmethod
    def step(self, events: List[Event]) -> Optional["GameScene"]:
        pass
