from typing import Any
from local_runner.comms import Message


def censor(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: censor(val) if key.lower() != "token" else "***********" for key, val in value.items()}
    elif isinstance(value, list):
        return [censor(val) for val in value]
    return value


def censored(message: Message) -> Message:
    return Message(
        type=message.type,
        payload=censor(message.payload)
    )
