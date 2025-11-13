from PyQt6.QtWidgets import QWidget


class PWidget(QWidget):


    def __init__(self):
        super().__init__()

        self.animating = False

    def animate(self, data=None):
        return

    def _release_anim_lock(self):
        self.animating = False

    def switch_gif(self, path, loop_count):
        return