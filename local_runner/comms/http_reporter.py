import requests
from .dtos import Request, HeartbeatResponse, UpdateMessage, Result
from .base import Reporter


class HttpReporter(Reporter):
    def __init__(self, session: requests.Session):
        self.session = session

    @staticmethod
    def _make_headers(request: Request):
        return {
            "Authorization": f"Bearer {request.token}",
            "Content-Type": "application/json"
        }

    def heartbeat(self, request: Request) -> HeartbeatResponse:
        path = f"/api/v1/session/{request.session_id}/heartbeat"
        url = request.state_service_url + path
        body = {
            "blockIndex": request.block_index
        }
        response = self.session.post(url, json=body, headers=self._make_headers(request))
        response.raise_for_status()
        return HeartbeatResponse.from_dict(response.json())

    def report_result(self, request: Request, result: Result) -> None:
        path = f"/api/v1/session/{request.session_id}/result"
        url = request.state_service_url + path
        body = result.to_dict()
        response = self.session.post(url, json=body, headers=self._make_headers(request))
        response.raise_for_status()

    def report_update(self, request: Request, update: UpdateMessage) -> None:
        path = f"/api/v1/session/{request.session_id}/update"
        url = request.state_service_url + path
        body = update.to_dict()
        response = self.session.post(url, json=body, headers=self._make_headers(request))
        response.raise_for_status()
