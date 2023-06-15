from promptops.shells.zsh import Zsh
from promptops.shells.bash import Bash
from promptops.shells.fish import Fish
from promptops.shells.base import NoopShell
import os
import psutil
import logging


_shells = {
    "zsh": Zsh,
    "bash": Bash,
    "fish": Fish,
}


def get_shell_name():
    proc = psutil.Process(os.getpid())

    path = []
    while proc is not None and proc.pid > 0:
        try:
            name = proc.name()
        except TypeError:
            name = proc.name

        name = os.path.splitext(name)[0]
        path = [name] + path

        if name in _shells:
            logging.debug(f"found shell: {'/'.join(path)}")
            return name

        try:
            proc = proc.parent()
        except TypeError:
            proc = proc.parent

    from promptops.feedback import feedback

    feedback(
        {
            "event": "shell_not_found",
            "path": "/".join(path),
        }
    )
    logging.debug(f"shell not supported: {'/'.join(path)}")
    return None


def get_shell():
    shell_name = get_shell_name()
    if shell_name is None:
        return NoopShell()
    return _shells[shell_name]()
