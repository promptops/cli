import asyncio
from asyncio import Queue
from dataclasses import dataclass
from typing import Callable, List, Optional
import subprocess


@dataclass
class Result:
    exit_code: Optional[int] = None
    error: Optional[Exception] = None


@dataclass
class Request:
    cmd: str
    args: List[str]
    on_started: Callable
    on_completed: Callable


@dataclass
class Status:
    queued: int
    running: int
    completed: int


class Manager:
    def __init__(self, parallelism: int = 1):
        self._queue = Queue()
        self.parallelism = max(parallelism, 1)
        self.busy = 0
        self.completed = 0
        self.worker_tasks = []

    def start(self):
        for _ in range(self.parallelism):
            worker = asyncio.create_task(self.worker())
            self.worker_tasks.append(worker)

    async def worker(self):
        while True:
            request = await self._queue.get()
            if request is None:
                # shutdown
                return
            self.busy += 1
            try:
                await self.run(request)
            except Exception as e:
                request.on_completed(Result(exit_code=None, error=e))
            finally:
                # just in case we decide to call join() on the queue
                self._queue.task_done()
                self.busy -= 1
                self.completed += 1

    async def queue(self, request: Request):
        await self._queue.put(request)

    def status(self) -> Status:
        return Status(queued=self._queue.qsize(), running=self.busy, completed=self.completed)

    @staticmethod
    async def run(request: Request):
        process = await asyncio.create_subprocess_exec(
            request.cmd,
            *request.args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        request.on_started(process.stdout, process.stderr)

        await process.wait()
        request.on_completed(Result(exit_code=process.returncode))

    async def stop(self, timeout: Optional[float] = None):
        for _ in self.worker_tasks:
            await self._queue.put(None)

        if timeout is not None:
            await asyncio.wait_for(asyncio.gather(*self.worker_tasks), timeout=timeout)
        else:
            await asyncio.gather(*self.worker_tasks)
