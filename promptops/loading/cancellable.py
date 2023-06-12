import threading

from promptops.loading import Simple, animate
from promptops.loading.multi import MultiLoader


class CancellableSimpleLoader:
    def __init__(self, text: str):
        self.text = text
        loader = Simple(text)
        self.event = threading.Event()
        fps = 10
        self.t = threading.Thread(target=animate, args=(loader, self.event), kwargs=dict(fps=fps), daemon=True)
        self.t.start()


    def stop(self):
        self.event.set()
        self.t.join()


class CancellableMultiLoader:
    def __init__(self, text: str, start_queue, done_queue):
        self.text = text
        loader = MultiLoader(text, start_queue, done_queue)
        self.event = threading.Event()
        fps = 10
        self.t = threading.Thread(target=animate, args=(loader, self.event), kwargs=dict(fps=fps), daemon=True)
        self.t.start()


    def stop(self):
        self.event.set()
        self.t.join()
