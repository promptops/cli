import sys
import colorama

LINE_UP = '\033[1A'


class LoadingBase(object):
    def __init__(self, stream=None):
        if stream is None:
            stream = sys.stdout
        self._stream = stream
        self._step = 0
        self._written_lines = 0

    def step(self):
        self.clear()
        self._draw()
        self._step += 1

    def _draw(self):
        raise NotImplementedError()

    def reset(self):
        self._step = 0

    def clear(self):
        if self._written_lines == 0:
            return
        self._stream.write(colorama.ansi.clear_line() + "\r")
        for i in range(self._written_lines - 1):
            self._stream.write(LINE_UP + colorama.ansi.clear_line() + "\r")
        self._written_lines = 0
