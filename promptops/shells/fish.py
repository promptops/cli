import subprocess
import time

from .base import Shell
from .base import reverse_readline, accept_command
from promptops.scrub_secrets import scrub_lines
import os
import logging


def _is_start_line(line):
    return line.startswith("- cmd: ")


class Fish(Shell):
    def __init__(self, history_file: str = None):
        if not history_file:
            history_file = os.getenv("HISTFILE", "~/.local/share/fish/fish_history")
            if not os.path.exists(os.path.expanduser(history_file)):
                history_file = "~/.config/fish/fish_history"

        super().__init__(history_file)

    def _get_cmds_from_lines(self, lines):
        commands = []
        for line in lines:
            if _is_start_line(line):
                cmd = line.split("- cmd: ")[1].rstrip()
                # unescape see https://stackoverflow.com/a/57192592
                try:
                    cmd = cmd.encode("latin-1", "backslashreplace").decode("unicode-escape")
                    if accept_command(cmd):
                        commands.append(cmd)
                except UnicodeDecodeError:
                    logging.debug("UnicodeDecodeError at line: ", line)
        return commands

    def get_recent_history(self, look_back: int = 10):
        fname = os.path.expanduser(self.history_file)
        commands = []
        for line in reverse_readline(fname):
            if len(commands) >= look_back:
                break
            if _is_start_line(line):
                cmd = line.split("- cmd: ")[1].rstrip()
                # unescape see https://stackoverflow.com/a/57192592
                try:
                    cmd = cmd.encode("latin-1", "backslashreplace").decode("unicode-escape")
                    if accept_command(cmd):
                        commands.append(cmd)
                except UnicodeDecodeError:
                    logging.debug("UnicodeDecodeError at line: ", line)
        return scrub_lines(fname, list(reversed(commands)))

    def add_to_history(self, script):
        with open(os.path.expanduser(self.history_file), 'a') as history:
            entry = f'- cmd: {script}\n   when: {time.time()}\n'
            history.write(entry)

    def get_config(self):
        return """
function um -d "your CLI assistant"
    command um $argv
    builtin history merge
end
""".strip()

    def _get_config_file(self):
        return "~/.config/fish/config.fish"
