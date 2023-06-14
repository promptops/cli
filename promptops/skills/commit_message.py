import logging

import requests
from promptops import settings
from promptops import user
from promptops import trace


def entry_point(args):
    pass


def get_commit_message(diff: str, prev_commits: list[str]):
    req = {
        "trace_id": trace.trace_id,
        "diff": diff,
        "previous_commits": prev_commits,
    }
    logging.debug(f"request: {req}")
    response = requests.post(
        settings.endpoint + "/skills/commit_message",
        json={
            "trace_id": trace.trace_id,
            "diff": diff,
            "previous_commits": prev_commits,
        },
        headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
        },
    )
    if response.status_code != 200:
        logging.debug(f"response: [{response.status_code}] {response.text}")
    response.raise_for_status()
    data = response.json()
    return data.get("options", [])
