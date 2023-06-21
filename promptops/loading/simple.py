from promptops.loading.base import LoadingBase
import colorama


TWO_DOTS = "⠃⠆⡄⣀⢠⠰⠘⠉"
THREE_DOTS = "⠇⠦⠴⠸⠙⠋"
FOUR_DOTS = "⡇⣆⣤⣰⢸⠹⠛⠏"


class Simple(LoadingBase):
    def __init__(self, text: str, style=THREE_DOTS, stream=None):
        super().__init__(stream=stream)
        self._style = style
        self._text = text

    def _get_text(self):
        char = self._style[self._step % len(self._style)]
        return colorama.Fore.GREEN + char + colorama.Style.RESET_ALL + " " + self._text

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
