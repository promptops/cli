import threading
from contextlib import contextmanager


def animate(loader, event: threading.Event, fps=10):
    while not event.is_set():
        loader.step()
        event.wait(1 / fps)
    loader.clear()


@contextmanager
def loading_animation(loader, fps=10):
    event = threading.Event()
    t = threading.Thread(target=animate, args=(loader, event), kwargs=dict(fps=fps), daemon=True)
    t.start()
    try:
        yield
    finally:
        event.set()
        t.join()
