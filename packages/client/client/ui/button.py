from typing import Callable, Tuple, Any
from direct.gui.DirectButton import DirectButton
from panda3d.core import TextNode


class Button:
    def __init__(
        self, x: int, y: int, width: int, height: int, text: str, font_size: int = 14
    ):
        screen_width = base.win.getXSize()
        screen_height = base.win.getYSize()

        px = (x + width / 2) / screen_width * 2 - 1
        py = 1 - (y + height / 2) / screen_height * 2

        scale_x = width / screen_width
        scale_y = height / screen_height

        self.button = DirectButton(
            text=text,
            pos=(px, 0, py),
            scale=(scale_x, 1, scale_y),
            text_scale=(font_size / 100, font_size / 100),
            relief="raised",
            frameColor=(0.3, 0.5, 0.3, 1),
            text_fg=(1, 1, 1, 1),
            command=self._on_click,
            rolloverSound=None,
            clickSound=None,
            text_align=TextNode.ACenter,
        )

        self.click_callback = None

    def set_click_callback(
        self, callback: Callable[[Tuple[float, float]], Any]
    ) -> None:
        self.click_callback = callback

    def _on_click(self) -> None:
        if self.click_callback:
            # For DirectButton, we don't have direct access to mouse position
            # So we'll pass (0, 0) as a placeholder or can use base.mouseWatcherNode
            # to get the actual mouse position if needed
            mouse_pos = (0, 0)
            if hasattr(base, "mouseWatcherNode") and base.mouseWatcherNode.hasMouse():
                mouse_pos = (
                    base.mouseWatcherNode.getMouseX(),
                    base.mouseWatcherNode.getMouseY(),
                )
            self.click_callback(mouse_pos)

    def destroy(self) -> None:
        if self.button:
            self.button.destroy()
            self.button = None
