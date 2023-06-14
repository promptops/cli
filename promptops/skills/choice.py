from dataclasses import dataclass


@dataclass
class Choice:
    id: str
    text: str
    parameters: dict
