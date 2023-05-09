from promptops.loading.base import LoadingBase
import colorama


class Simple(LoadingBase):
    # _STEPS = "⠃⠆⡄⣀⢠⠰⠘⠉"
    # _STEPS = "⡇⣆⣤⣰⢸⠹⠛⠏"
    _STEPS = "⠇⠦⠴⠸⠙⠋"

    def __init__(self, text: str):
        super().__init__()
        self._text = text

    def _get_text(self):
        char = self._STEPS[self._step % len(self._STEPS)]
        return colorama.Fore.GREEN + char + colorama.Style.RESET_ALL + " " + self._text

    def _draw(self):
        self._stream.write(self._get_text() + " ")
        self._stream.flush()
        self._written_lines = 1
