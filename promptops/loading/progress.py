import threading
import sys
import queue


class ProgressSpinner:
    def __init__(self, total):
        self.total = total
        self.queue = queue.Queue()
        self.current = 0
        self.thread = threading.Thread(target=self.__progress_spinner, args=(self.total, self.queue))
        self.thread.start()

    def increment(self, completed):
        self.current += completed
        self.queue.put(self.current)
        if self.current >= self.total:
            self.thread.join()

    def set(self, completed):
        self.queue.put(completed)
        self.current = completed
        if completed >= self.total:
            self.thread.join()

    @staticmethod
    def __progress_spinner(total, completed_queue):
        completed = min(completed_queue.get(), total)
        percent = completed / total
        sys.stdout.write("\rProgress: [{0:50s}] {1:.1f}%".format("#" * int(percent * 50), percent * 100))
        sys.stdout.flush()

        while True:
            completed = min(completed_queue.get(), total)
            percent = completed / total
            sys.stdout.write("\rProgress: [{0:50s}] {1:.1f}%".format("#" * int(percent * 50), percent * 100))
            sys.stdout.flush()

            if completed >= total:
                sys.stdout.write("\n")
                sys.stdout.flush()
                break

