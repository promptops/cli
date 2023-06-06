import atexit
import typing
from concurrent.futures import ThreadPoolExecutor

from promptops import trace
from promptops import settings
from promptops import user
import requests


class FeedbackProcessor:
    def __init__(self):
        self.workers_pool = ThreadPoolExecutor(max_workers=2)
        atexit.register(self.shutdown)

    @staticmethod
    def _send(payload: dict):
        requests.post(settings.endpoint + "/feedback", json={
            "trace_id": trace.trace_id,
            **payload
        }, headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}"
        })
        # feedback is best-effort, so we don't raise for status

    def submit(self, payload: dict):
        self.workers_pool.submit(self._send, payload)

    def shutdown(self):
        self.workers_pool.shutdown()


_processor: typing.Optional[FeedbackProcessor] = None


def feedback(payload: dict):
    global _processor
    if _processor is None:
        _processor = FeedbackProcessor()
    _processor.submit(payload)
