from local_runner.comms import Reporter, Request, Message, Code
from local_runner import exec
from local_runner import handler
from local_runner import config
import pytest


@pytest.mark.asyncio
async def test_handler():
    mgr = exec.Manager(2)
    mgr.start()

    class MockReporter(Reporter):
        def heartbeat(self, request: Request):
            print(f"heartbeat: {request}")
            return None

        def report_update(self, request, message):
            print(f"report update: {message}")

        def report_result(self, request, message):
            print(f"report result: {message}")

    reporter = MockReporter()
    h = handler.Handler(mgr, reporter, config.default())
    for i in range(1, 4):
        await h.handle(Message(
            type="request",
            payload=Request(
                block_index=1,
                session_id=f"test-{i}",
                code=Code(
                    type="python",
                    content=f"import time;print('{i}hello world');time.sleep({i / 10});print('{i}bye world')"
                ),
                state_service_url="http://localhost:8080",
                token="deadbeef"
            ).to_dict()
        ).to_dict(), None)
    await mgr.stop()

    assert True
