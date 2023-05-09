from promptops.loading.base import LoadingBase


class Pong(LoadingBase):
    _DOTS = "⠁⠂⠄⡀⠈⠐⠠⢀"
    _PADDLES = "╵╷"

    def __init__(self, width=5):
        super().__init__()
        self._use_left_dots = True
        self._width = width
        self._height = 4
        self._x = 0
        self._y = 0
        self._dx = 1
        self._dy = 1
        self._paddle_left = 0
        self._paddle_right = 1

    def _draw(self):
        s = self._PADDLES[self._paddle_left] + " " * self._x + self._DOTS[self._y + (0 if self._use_left_dots else self._height)] + " " * (self._width - 1 - self._x) + self._PADDLES[self._paddle_right]
        self._stream.write(s + "\n")
        self._written_lines = 2

        self._x += self._dx
        self._y += self._dy
        if self._x < 0 or self._x >= self._width:
            self._dx *= -1
            self._x = max(0, min(self._x, self._width - 1))
            self._use_left_dots = not self._use_left_dots
        if self._y < 0 or self._y >= self._height:
            self._dy *= -1
            self._y = max(0, min(self._y, self._height - 1))
        if self._dx > 0:
            self._paddle_right = self._y // (self._height // 2)
        else:
            self._paddle_left = self._y // (self._height // 2)
