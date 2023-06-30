from dataclasses import dataclass
from typing import List


@dataclass
class Result:
    script: str = None
    scripts: List[str] = None
    explanation: str = None
    lang: str = "shell"
    origin: str = "promptops"
    score: float = 1

    @staticmethod
    def from_dict(data: dict) -> "Result":
        return Result(
            script=data["script"],
            explanation=data.get("explanation"),
            lang=data.get("lang", "shell"),
            origin=data.get("origin", "promptops"),
        )
