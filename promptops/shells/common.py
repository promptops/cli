from promptops.shells.zsh import Zsh
from promptops.shells.bash import Bash
import os


def get_shell():
    shell = os.environ.get("SHELL")
    if shell == "/bin/bash":
        return Bash()
    else:
        return Zsh()
