import abc
from .dtos import Request, HeartbeatResponse, Result, UpdateMessage


class Reporter(abc.ABC):
    @abc.abstractmethod
    def heartbeat(self, request: Request) -> HeartbeatResponse:
        pass

    @abc.abstractmethod
    def report_result(self, request: Request, result: Result) -> None:
        pass

    @abc.abstractmethod
    def report_update(self, request: Request, update: UpdateMessage) -> None:
        pass
