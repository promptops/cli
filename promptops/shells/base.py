import re
import os
from promptops.scrub_secrets import scrub_lines


def _is_start_line(line):
    return re.match(r"^: \d+:\d+;.+", line) is not None


CMDS_TO_EXCLUDE = [
    "um",
    "qq",
    "promptops query",
    "python -m promptops.main query",
]


def accept_command(cmd: str) -> bool:
    if cmd.strip() == "":
        return False
    for cmd_to_exclude in CMDS_TO_EXCLUDE:
        if cmd == cmd_to_exclude or cmd.startswith(cmd_to_exclude + " "):
            return False
    return True


def filter_commands(commands: list[str]):
    return filter(accept_command, commands)


def reverse_readline(filename, buf_size=8192, transform: callable = None):
    """A generator that returns the lines of a file in reverse order"""
    with open(filename, "rb") as fh:
        segment = None
        offset = 0
        fh.seek(0, os.SEEK_END)
        file_size = remaining_size = fh.tell()
        extra = b""
        while remaining_size > 0:
            offset = min(file_size, offset + buf_size)
            fh.seek(file_size - offset)
            block = fh.read(min(remaining_size, buf_size)) + extra
            remaining_size -= buf_size

            if transform is not None:
                block, extra_transform = transform(block)
            else:
                extra_transform = b""

            for i in range(min(8, len(block))):
                try:
                    buffer = block[i:].decode(encoding="utf-8")
                    extra = block[:i] + extra_transform
                    break
                except UnicodeDecodeError:
                    continue
            else:
                extra = block + extra_transform
                continue
            lines = buffer.split("\n")
            # The first line of the buffer is probably not a complete line so
            # we'll save it and append it to the last line of the next buffer
            # we read
            if segment is not None:
                # If the previous chunk starts right from the beginning of line
                # do not concat the segment to the last line of new chunk.
                # Instead, yield the segment first
                if buffer[-1] != "\n":
                    lines[-1] += segment
                else:
                    lines = lines[:-1]
                    yield segment
            segment = lines[0]
            # iterate in reverse
            for index in range(len(lines) - 1, 0, -1):
                yield lines[index]
        # Don't yield None if the file was empty
        if segment is not None:
            yield segment


def readline(filename, buf_size=8192, transform: callable = None):
    with open(filename, "rb") as fh:
        segment = None
        extra = b""
        while True:
            data = fh.read(buf_size)
            if not data:
                break
            block = extra + data
            if transform is not None:
                block, extra_transform = transform(block)
            else:
                extra_transform = b""
            for i in range(min(8, len(block))):
                try:
                    buffer = block[i:].decode(encoding="utf-8")
                    extra = block[:i] + extra_transform
                    break
                except UnicodeDecodeError:
                    continue
            else:
                extra = block + extra_transform
                continue
            lines = buffer.split("\n")
            # The last line of the buffer is probably not a complete line so
            # we'll save it and append it to the first line of the next buffer
            # we read
            if segment is not None:
                lines[0] = segment + lines[0]
            for line in lines[:-1]:
                yield line
            segment = lines[-1]
        # Don't yield None if the file was empty
        if segment is not None:
            yield segment


class Shell:
    def __init__(self, history_file):
        self.history_file = history_file

    def get_full_history(self):
        history = self._read_history_file()
        cmds = self._get_cmds_from_lines(history)
        return scrub_lines(self.history_file, list(filter_commands(cmds)))

    def _read_history_file(self):
        fname = os.path.expanduser(self.history_file)
        with open(fname, "r", encoding="utf-8", errors="ignore") as f:
            return [line.strip() for line in f if line.strip() != ""]

    def _get_cmds_from_lines(self, history):
        raise NotImplementedError()

    def get_recent_history(self, look_back: int = 10):
        raise NotImplementedError()


class NoopShell(Shell):
    def _get_cmds_from_lines(self, history):
        pass

    def __init__(self):
        super().__init__(None)

    def get_full_history(self):
        return []

    def get_recent_history(self, look_back: int = 10):
        return []
