import queue

from promptops.loading.base import LoadingBase
import colorama

THREE_DOTS = "⠇⠦⠴⠸⠙⠋"
THREE_DOTS_DONE = ""


class MultiLoader(LoadingBase):
    def __init__(self, start_queue, done_queue, style=THREE_DOTS):
        super().__init__()
        self._style = style
        self._start_queue = start_queue
        self._items = []
        self._done_queue = done_queue
        self._done = []


    def _get_text(self):
        self._update()
        builder = ""
        for item in self._items:
            char = self._style[self._step % len(self._style)]
            if item in self._done:
                char = "x"
            builder += colorama.Fore.GREEN + char + colorama.Style.RESET_ALL + " " + item + "\n"
        return builder


    def _update(self):
        try:
            self._done.append(self._done_queue.get(block=False))
        except queue.Empty:
            pass
        try:
            self._items.append(self._start_queue.get(block=False))
        except queue.Empty:
            pass


    def _draw(self):
        txt = self._get_text() + " "
        self._stream.write(txt)
        self._stream.flush()
        self._written_lines = len(txt.split("\n"))


def loader(text: str, style: str = THREE_DOTS, color=colorama.Fore.GREEN):
    step = 0

    def _get_text(advance=True):
        nonlocal step
        char = style[step % len(style)]
        if advance:
            step += 1
        return colorama.Style.BRIGHT + color + char + colorama.Style.RESET_ALL + "  " + text

    return _get_text


