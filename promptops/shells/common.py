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


def _resolve_shell():
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
            return _shells[name]()

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
    return NoopShell()


def get_shell():
    shell = _resolve_shell()
    return shell
