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

        for line in reversed(self._get_added_history()):
            if len(commands) >= look_back:
                break
            if accept_command(line):
                commands.append(line)

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
                else:
                    if buffer:
                        cmd = buffer.lstrip("\n")
                        if accept_command(cmd):
                            commands.append(cmd)
                    buffer = "\n" + line
        return scrub_lines(fname, list(reversed(commands)))

    def get_full_history(self):
        fname = os.path.expanduser(self.history_file)
        lines = list(readline(fname, transform=unmetafy))
        commands = filter(accept_command, self._get_cmds_from_lines(lines))
        return scrub_lines(fname, list(commands) + list(filter(accept_command, self._get_added_history())))

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
                if buffer.endswith("\\"):
                    buffer = buffer[:-1]
            else:
                line = line.rstrip()
                if line.endswith("\\"):
                    buffer += "\n" + line[:-1]
                else:
                    if buffer:
                        buffer = buffer.lstrip("\n")
                        commands.append(buffer + "\n" + line)
                    else:
                        commands.append(line.lstrip("\n"))
                    buffer = ""
        if buffer != "" and not buffer.endswith("\\"):
            commands.append(buffer.lstrip("\n"))
        return commands

    def get_config(self):
        return f"""
um() {{
    command um $@
    if [[ -f {self.temp_history_file} ]]; then
        while IFS= read -r line; do
            test -n "$line" && print -s "$line"
        done < {self.temp_history_file}
        rm {self.temp_history_file}
    fi
}}""".strip()

    def _get_config_file(self):
        return "~/.zshrc"
