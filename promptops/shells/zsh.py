import re

from promptops.shells.base import Shell, accept_command, reverse_readline, readline
from promptops.scrub_secrets import scrub_lines
import os


def _is_zsh_start_line(line):
    return re.match(r"^: \d+:\d+;.+", line) is not None


_meta_char = 0x83


def unmetafy(cmd: bytes) -> (bytes, bytes):
    i = 0
    result = b""
    while i < len(cmd):
        if cmd[i] == _meta_char:
            if i + 1 >= len(cmd):
                return result, cmd[i:]
            result += bytes([cmd[i+1] ^ 32])
            i += 1
        else:
            result += cmd[i: i+1]
        i += 1
    return result, b""


class Zsh(Shell):
    def __init__(self, history_file: str = None):
        if not history_file:
            history_file = os.getenv("HISTFILE", "~/.zsh_history")
        super().__init__(history_file)

    def get_recent_history(self, look_back: int = 10):
        fname = os.path.expanduser(self.history_file)
        buffer = ""
        commands = []
        starting = True
        for line in reverse_readline(fname, transform=unmetafy):
            if starting and line == "":
                continue
            starting = False
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

    def get_full_history(self):
        fname = os.path.expanduser(self.history_file)
        lines = list(readline(fname, transform=unmetafy))
        commands = filter(accept_command, self._get_cmds_from_lines(lines))
        return scrub_lines(fname, list(commands))

    def _get_cmds_from_lines(self, lines):
        buffer = ""
        commands = []
        # find the index of the last non-empty line
        i = len(lines) - 1
        for i in range(len(lines) - 1, -1, -1):
            if lines[i] != "":
                break
        for line in lines[:i+1]:
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
