from dataclasses import dataclass
from typing import Any


@dataclass
class Code:
    type: str = "python"
    content: str = ""

    def to_dict(self):
        return {
            "type": self.type,
            "content": self.content,
        }

    @staticmethod
    def from_dict(d: dict) -> "Code":
        return Code(
            type=d.get("type", ""),
            content=d.get("content", ""),
        )


@dataclass
class Request:
    token: str
    session_id: str
    block_index: int
    code: Code
    state_service_url: str

    def to_dict(self):
        return {
            "token": self.token,
            "sessionId": self.session_id,
            "blockIndex": self.block_index,
            "code": self.code.to_dict(),
            "stateServiceUrl": self.state_service_url,
        }

    @staticmethod
    def from_dict(d: dict) -> "Request":
        return Request(
            token=d.get("token", ""),
            session_id=d.get("sessionId", ""),
            block_index=d.get("blockIndex", 0),
            code=Code.from_dict(d.get("code", {})),
            state_service_url=d.get("stateServiceUrl", ""),
        )


@dataclass
class Message:
    type: str = ""
    payload: Any = None

    def to_dict(self):
        return {
            "type": self.type,
            "payload": self.payload,
        }

    @staticmethod
    def from_dict(d: dict) -> "Message":
        return Message(
            type=d.get("type", ""),
            payload=d.get("payload"),
        )


@dataclass
class HeartbeatResponse:
    signal: str
    metadata: Any

    def to_dict(self):
        return {
            "signal": self.signal,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(d: dict) -> "HeartbeatResponse":
        return HeartbeatResponse(
            signal=d.get("signal", ""),
            metadata=d.get("metadata", ""),
        )


@dataclass
class UpdateMessage:
    message_type: str
    block_index: int
    data: "StreamData"
    time: int

    def to_dict(self):
        return {
            "messageType": self.message_type,
            "blockIndex": self.block_index,
            "data": self.data.to_dict(),
            "time": self.time,
        }


@dataclass
class Result:
    status: int
    reason: str
    result: dict
    block_index: int

    def to_dict(self):
        return {
            "status": self.status,
            "reason": self.reason,
            "result": self.result,
            "blockIndex": self.block_index,
        }


@dataclass
class StreamData:
    stream: str
    data: str

    def to_dict(self):
        return {
            "stream": self.stream,
            "data": self.data,
        }


@dataclass
class StructuredOutput:
    data: str
    encoding: str

    def to_dict(self):
        return {
            "data": self.data,
            "encoding": self.encoding,
        }
