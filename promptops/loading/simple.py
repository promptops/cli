from promptops.loading.base import LoadingBase
import colorama


TWO_DOTS = "⠃⠆⡄⣀⢠⠰⠘⠉"
THREE_DOTS = "⠇⠦⠴⠸⠙⠋"
FOUR_DOTS = "⡇⣆⣤⣰⢸⠹⠛⠏"


class Simple(LoadingBase):
    def __init__(self, text: str, style=THREE_DOTS):
        super().__init__()
        self._style = style
        self._text = text

    def _get_text(self):
        char = self._style[self._step % len(self._style)]
        return colorama.Fore.GREEN + char + colorama.Style.RESET_ALL + " " + self._text

    def _draw(self):
        self._stream.write(self._get_text() + " ")
        self._stream.flush()
        self._written_lines = 1


def loader(text: str, style: str = THREE_DOTS, color=colorama.Fore.GREEN):
    step = 0

    def _get_text(advance=True):
        nonlocal step
        char = style[step % len(style)]
        if advance:
            step += 1
        return colorama.Style.BRIGHT + color + char + colorama.Style.RESET_ALL + "  " + text

    return _get_text
