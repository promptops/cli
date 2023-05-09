import asyncio
from local_runner import comms
from local_runner import exec
from .censor import censored
from local_runner.config import Config
from local_runner.comms import dtos
import time
import logging


class Handler:
    def __init__(self, process_mgr: exec.Manager, reporter: comms.Reporter, cfg: Config):
        self.process_mgr = process_mgr
        self.reporter = reporter
        self.cfg = cfg

    async def handle(self, data: dict, _):
        message = comms.Message.from_dict(data)
        logging.debug(f"got message: {censored(message)}")
        if message.type == "request":
            req = comms.Request.from_dict(message.payload)
            truncated = "<EMPTY>"
            if req.code.content:
                truncated = req.code.content.split("\n")[0]
                if len(truncated) > 50:
                    truncated = truncated[:50] + "..."
            logging.info(f"received {truncated}")
            exec_request = self.make_exec_request(req)
            await self.process_mgr.queue(exec_request)

    def make_exec_request(self, request: comms.Request) -> exec.Request:
        def on_started(stdout, stderr):
            print(f"started session: {request.session_id}")

            async def report(stream: str, data: str):
                payload = dtos.StreamData(stream=stream, data=data)
                self.reporter.report_update(request, dtos.UpdateMessage(
                    message_type="stream",
                    data=payload,
                    block_index=request.block_index,
                    time=int(time.time() * 1000)
                ))

            async def read_stream(stream_name: str, stream):
                async for line in stream:
                    # line is bytes
                    decoded = line.decode("utf-8")
                    print(f"{stream_name}> {decoded.rstrip()}")
                    await report(stream_name, decoded)

            asyncio.create_task(read_stream("stdout", stdout))
            asyncio.create_task(read_stream("stderr", stderr))

        def on_completed(result: exec.Result):
            print(f"Process completed, session: {request.session_id}, result: {result}")
            api_result = dtos.Result(
                status=result.exit_code if result.exit_code is not None else 1,
                reason=str(result.error) if result.error else None,
                result={},
                block_index=request.block_index,
            )
            if result.error and api_result.status == 0:
                api_result.status = 1
            self.reporter.report_result(request, api_result)

        if request.code.type == "python":
            return exec.Request(cmd=self.cfg.python_path, args=["-c", request.code.content], on_started=on_started,
                                on_completed=on_completed)
        elif request.code.type == "shell":
            return exec.Request(cmd=self.cfg.shell_path, args=["-c", request.code.content], on_started=on_started,
                                on_completed=on_completed)
        raise ValueError(f"Unknown code type: {request.code.type}")
