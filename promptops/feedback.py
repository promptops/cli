from promptops import trace
from promptops import settings
from promptops import user
import requests


def feedback(payload: dict):
    requests.post(settings.endpoint + "/feedback", json={
        "trace_id": trace.trace_id,
        **payload
    }, headers={
        "user-agent": f"promptops-cli; user_id={user.user_id()}"
    })
    # feedback is best-effort, so we don't raise for status
