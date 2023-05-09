from dataclasses import dataclass

import requests

from promptops import settings
from promptops import trace
from promptops import user


@dataclass
class Result:
    script: str
    explanation: str = None
    lang: str = "shell"
    origin: str = "promptops"

    @staticmethod
    def from_dict(data: dict) -> 'Result':
        return Result(
            script=data["script"],
            explanation=data.get("explanation"),
            lang=data.get("lang", "shell"),
            origin=data.get("origin", "promptops"),
        )


def query(*, q: str) -> list[Result]:
    response = requests.post(settings.endpoint + "/query", json={
        "query": q,
        "explanation": settings.request_explanation,
        "model": settings.model,
        "trace_id": trace.trace_id,
    }, headers={
        "user-agent": f"promptops-cli; user_id={user.user_id}",
    })
    if response.status_code != 200:
        raise Exception(f"there was problem with the response, status: {response.status_code}, text: {response.text}")
    data = response.json()
    return [Result.from_dict(entry) for entry in data["suggestions"]]
