import threading
import sys
import queue


class ProgressSpinner:
    def __init__(self, total):
        self.total = total
        self.current = 0
        self._finished = False

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
        sys.stdout.write("\rProgress: [{0:50s}] {1:.1f}%".format("#" * int(percent * 50), percent * 100))
        sys.stdout.flush()

        if completed >= self.total:
            sys.stdout.write("\n")
            sys.stdout.flush()
            self._finished = True
