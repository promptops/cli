import threading
import sys
import queue


class ProgressSpinner:
    def __init__(self, total, header="", text="Progress: "):
        self.total = total
        self.current = 0
        self._finished = False
        self._text = text
        self._static_lines_written = 0
        self._dyn_lines_written = 0
        if header:
            self._static_lines_written = len(header.split("\n"))
            sys.stdout.write(f"{header}\n")

    def increment(self, completed):
        self.current += completed
        self._update()

    def set(self, completed):
        self.current = completed
        self._update()

    def _update(self):
        if self._finished:
            return
        completed = min(self.current, self.total)
        percent = completed / self.total
        written_text = "\r{0}: [{1:50s}] {2:.1f}%".format(self._text, "#" * int(percent * 50), percent * 100)
        sys.stdout.write(written_text)
        sys.stdout.flush()
        self._dyn_lines_written = 1

        if completed >= self.total:
            sys.stdout.write("\n")
            sys.stdout.flush()
            self._dyn_lines_written += 1
            self._finished = True

    def clear(self):
        total_lines = self._static_lines_written + self._dyn_lines_written
        sys.stdout.write("\x1b[2K")
        for _ in range(total_lines - 1):
            sys.stdout.write("\x1b[1A\x1b[2K")
        sys.stdout.write("\r")
        sys.stdout.flush()
