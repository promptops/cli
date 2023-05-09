from detect_secrets import SecretsCollection
from detect_secrets.settings import default_settings
import re
import os


def _scrub_secrets(filename, lines):
    secrets = SecretsCollection()
    lines_to_secrets = {}

    with default_settings():
        secrets.scan_file(filename)
        for secret in secrets.data[filename]:
            if lines_to_secrets.get(secret.line_number - 1) is None:
                lines_to_secrets[secret.line_number - 1] = [secret]
            else:
                lines_to_secrets[secret.line_number - 1].append(secret)

    for index, secrets in lines_to_secrets.items():
        for secret in secrets:
            lines[index] = lines[index].replace(secret.secret_value, "<SECRET>")

    return lines


def _is_start_line(line):
    return re.match(r"^: \d+:\d+;.+", line) is not None


class Shell:

    def __init__(self, history_file):
        self.history_file = history_file

    def process_history(self):
        alias = os.getenv("PO_ALIAS", "promptops")
        fname = os.path.expanduser(self.history_file)
        with open(fname, "r") as f:
            lines = _scrub_secrets(fname, list(f))
            return lines

    def get_full_history(self):
        fname = os.path.expanduser(self.history_file)
        with open(fname, "r") as f:
            lines = _scrub_secrets(fname, list(f))
            return [line.strip() for line in lines]


    def get_history(self, look_back: int = 10):
        alias = os.getenv("PO_ALIAS", "promptops")
        fname = os.path.expanduser(self.history_file)
        # TODO: don't read the entire file, seek towards the end
        with open(fname, "r") as f:
            lines = _scrub_secrets(fname, list(f))

        lines = lines[-100:]

        buffer = ""
        commands = []
        # the first (from the bottom) is the current command, skip it
        is_first = True
        for l in reversed(lines):
            if len(commands) >= look_back:
                break
            if _is_start_line(l):
                cmd = l.split(";")[1].rstrip() + buffer
                if cmd.startswith(alias + " "):
                    cmd = cmd[len(alias + " "):]
                if not is_first:
                    commands.append(cmd)
                else:
                    is_first = False
                buffer = ""
            else:
                buffer = "\n" + l.rstrip() + buffer
        return list(reversed(commands))

    def config_script(self, alias: str):
        return f"""
        {alias}() {{
            export PO_ALIAS={alias};
            promptops -- $@
        }}
        """
