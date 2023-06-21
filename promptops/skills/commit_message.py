import logging

import requests
from promptops import settings
from promptops import user
from promptops import trace


def get_commit_message(diff: str, prev_commits: list[str], max_options: int = 3) -> list[str]:
    req = {
        "trace_id": trace.trace_id,
        "diff": diff,
        "previous_commits": prev_commits,
        "max_options": max_options,
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
