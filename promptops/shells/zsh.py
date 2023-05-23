import re

from promptops.shells.base import Shell, accept_command, reverse_readline
from promptops.scrub_secrets import scrub_lines
import os


def _is_zsh_start_line(line):
    return re.match(r"^: \d+:\d+;.+", line) is not None


class Zsh(Shell):
    def __init__(self, history_file: str = None):
        if not history_file:
            history_file = os.getenv("HISTFILE", "~/.zsh_history")
        super().__init__(history_file)

    def get_recent_history(self, look_back: int = 10):
        fname = os.path.expanduser(self.history_file)
        buffer = ""
        commands = []
        for line in reverse_readline(fname):
            if len(commands) >= look_back:
                break
            if _is_zsh_start_line(line):
                line = line.split(";")[1].rstrip()
                if line.endswith("\\"):
                    line = line[:-1]
                cmd = line + buffer
                buffer = ""
                if accept_command(cmd):
                    commands.append(cmd)
            else:
                line = line.rstrip()
                if line.endswith("\\"):
                    line = line[:-1]
                buffer = "\n" + line + buffer
        return scrub_lines(fname, list(reversed(commands)))

    def _get_cmds_from_lines(self, lines):
        buffer = ""
        commands = []
        for line in lines:
            if _is_zsh_start_line(line):
                if buffer != "":
                    commands.append(buffer)
                buffer = line.split(";")[1].rstrip()
            else:
                buffer += "\n" + line.rstrip()
            if buffer.endswith("\\"):
                buffer = buffer[:-1]
        if buffer != "" and not buffer.endswith("\\"):
            commands.append(buffer)
        return commands
