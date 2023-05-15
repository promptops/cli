from promptops.shells.base import Shell, reverse_readline, accept_command
from promptops.scrub_secrets import scrub_lines
import os


class Bash(Shell):
    def __init__(self, history_file: str = None):
        if not history_file:
            history_file = os.getenv("HISTFILE", "~/.bash_history")
        super().__init__(history_file)

    def get_recent_history(self, look_back: int = 10):
        fname = os.path.expanduser(self.history_file)
        buffer = ""
        commands = []
        for line in reverse_readline(fname):
            if len(commands) >= look_back:
                break
            current = line.rstrip()
            if current.endswith("\\"):
                buffer = current + "\n" + buffer
                continue
            else:
                if accept_command(buffer):
                    commands.append(buffer)
                buffer = current
        return scrub_lines(fname, list(reversed(commands)))

    def _get_cmds_from_lines(self, lines):
        buffer = ""
        commands = []
        for line in lines:
            buffer += "\n" + line.rstrip()
            if not line.endswith("\\"):
                commands.append(buffer.lstrip())
                buffer = ""
        return commands
