from promptops.shells.base import Shell


class Zsh(Shell):

    def __init__(self):
        super().__init__("~/.zsh_history")
