from promptops.query.explanation import ReturningThread
import pytest


def test_returns_value():
    rt = ReturningThread(lambda: 1)
    rt.start()
    assert rt.join() == 1


def test_returns_exception():
    rt = ReturningThread(lambda: 1 / 0)
    rt.start()
    with pytest.raises(ZeroDivisionError):
        rt.join()


def test_done_callback():
    rt = ReturningThread(lambda: 1)

    value = 0

    def on_done(t):
        nonlocal value
        value = t.result()

    rt.add_done_callback(on_done)
    rt.start()

    rt.join()
    assert value == 1
