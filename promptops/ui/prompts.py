from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.shortcuts import CompleteStyle
import shlex
from pathlib import Path


kb = KeyBindings()


EXIT = "~ctrl_c"
TOGGLE_CLARIFY_MODE = "~toggle_clarify_mode"
SKIP = TOGGLE_CLARIFY_MODE
GO_BACK = "~go_back"


@kb.add("c-c")
def _(event):
    event.app.exit(result=EXIT)


@kb.add("escape", eager=True)
def _(event):
    event.app.exit(result=GO_BACK)


@kb.add("c-b", eager=True)
def _(event):
    event.app.exit(result=GO_BACK)


@kb.add("c-r")
def _(event):
    event.app.exit(result=TOGGLE_CLARIFY_MODE)


class FileCompleter(Completer):
    def get_completions(self, document, complete_event):
        # TODO: use shlex.shlex to get the lexer for more accurate word boundary
        shlex.shlex()
        adjust = 0
        try:
            words = shlex.split(document.text)
            if document.text == "" or document.text[-1] == " ":
                words.append("")
        except ValueError:
            adjust = -1
            try:
                words = shlex.split(document.text + "'")
            except ValueError:
                words = shlex.split(document.text + '"')
        word_before_cursor = words[-1]
        path = Path(word_before_cursor).expanduser()

        if path.is_dir():
            for file in sorted(path.iterdir(), key=lambda x: str(x)):
                yield Completion(
                    shlex.quote(str(file)), start_position=-len(word_before_cursor) + adjust, display=str(file)
                )
        else:
            for file in sorted(path.parent.iterdir(), key=lambda x: str(x)):
                if file.name.startswith(path.name):
                    yield Completion(
                        shlex.quote(str(file)),
                        start_position=-len(word_before_cursor) + adjust,
                        display=str(file),
                    )


def confirm_command(prompt_text, show_go_back=True, message="> "):
    bottom_toolbar = HTML(
        "<b>[enter]</b> confirm <b>[ctrl+c]</b> exit"
        + (" <b>[esc]</b> or <b>[ctrl+b]</b> go back" if show_go_back else "")
    )
    user_input = prompt(
        message,
        default=prompt_text,
        bottom_toolbar=bottom_toolbar,
        key_bindings=kb,
        completer=FileCompleter(),
        complete_style=CompleteStyle.READLINE_LIKE,
    )
    return user_input


def confirm(prompt_text):
    message = f"> "
    bottom_toolbar = HTML("<b>[enter]</b> confirm <b>[esc]</b> or <b>[ctrl+b]</b> go back")
    user_input = prompt(message, default=prompt_text, bottom_toolbar=bottom_toolbar, key_bindings=kb)
    return user_input


def confirm_clarify(prompt_text):
    message = f"clarify: "
    bottom_toolbar = HTML("<b>[enter]</b> confirm <b>[ctrl+c]</b> exit <b>[escape]</b> or <b>[ctrl+b]</b> go back")
    user_input = prompt(message, default=prompt_text, bottom_toolbar=bottom_toolbar, key_bindings=kb)
    return user_input
