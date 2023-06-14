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


    def start(self):
        loader = Simple(self.text)
        self.event = threading.Event()
        fps = 10
        self.t = threading.Thread(target=animate, args=(loader, self.event), kwargs=dict(fps=fps), daemon=True)
        self.t.start()


class CancellableMultiLoader:
    def __init__(self, start_queue, done_queue):
        loader = MultiLoader(start_queue, done_queue)
        self.event = threading.Event()
        fps = 10
        self.t = threading.Thread(target=animate, args=(loader, self.event), kwargs=dict(fps=fps), daemon=True)
        self.t.start()


    def stop(self):
        self.event.set()
        self.t.join()
