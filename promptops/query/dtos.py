from dataclasses import dataclass


@dataclass
class Result:
    script: str
    explanation: str = None
    lang: str = "shell"
    origin: str = "promptops"

    @staticmethod
    def from_dict(data: dict) -> "Result":
        return Result(
            script=data["script"],
            explanation=data.get("explanation"),
            lang=data.get("lang", "shell"),
            origin=data.get("origin", "promptops"),
        )
