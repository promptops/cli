from promptops.shells.base import Shell


class Bash(Shell):
    def __init__(self):
        super().__init__("~/.bash_history")
