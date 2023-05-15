from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML

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


def confirm_command(prompt_text, show_go_back=True):
    message = f"> "
    bottom_toolbar = HTML(
        "<b>[enter]</b> confirm <b>[ctrl+c]</b> exit"
        + (" <b>[esc]</b> or <b>[ctrl+b]</b> go back" if show_go_back else "")
    )
    user_input = prompt(message, default=prompt_text, bottom_toolbar=bottom_toolbar, key_bindings=kb)
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
