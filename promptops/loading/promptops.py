import colorama


_chars = "⬢⬡"

alternating = "⬢⬡"
filled = "⬢"
outline = "⬡"


def loader(text: str, style: str = alternating, colors: list[str] = None):
    if colors is None:
        colors = [
            colorama.Fore.GREEN,
            colorama.Fore.CYAN,
            colorama.Fore.BLUE,
            colorama.Fore.LIGHTBLUE_EX,
            colorama.Fore.LIGHTCYAN_EX,
            colorama.Fore.LIGHTGREEN_EX,
        ]
    step = 0

    def _get_text(advance=True):
        nonlocal step
        char = style[step % len(style)]
        color = colors[step % len(colors)]
        if advance:
            step += 1
        return colorama.Style.BRIGHT + color + char + colorama.Style.RESET_ALL + "  " + text

    return _get_text
