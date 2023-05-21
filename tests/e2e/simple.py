import pexpect
import pyte
from promptops import settings
import os


class StreamWrapper:
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        self.stream.feed(data)

    def flush(self):
        pass


def simple():
    screen = pyte.Screen(80, 24)
    stream = pyte.Stream(screen, strict=False)
    wrapper = StreamWrapper(stream)

    try:
        child = pexpect.spawn(
            "um say test",
            encoding="utf-8",
            timeout=15,
            env={
                **os.environ,
                # make sure we use the stable endpoint
                "PROMPTOPS_ENDPOINT": settings.endpoint,
            },
        )
        child.logfile_read = wrapper
        print("spawned, waiting for echo")
        child.expect("✨ echo 'test'")
        print("found echo, attempting to select")
        attempts = 5
        while True:
            if attempts == 0:
                raise Exception("failed to select")
            index = child.expect_exact(["➜︎ \x1b[1m✨ echo 'test'\x1b[0m", pexpect.TIMEOUT], timeout=0.5)
            if index == 0:
                break
            print("timeout, sending down, attempts left", attempts)
            child.send("\x1b[B")
            attempts -= 1
        print("moved to echo, confirming")
        child.send("\n")
        print("sent newline, waiting for prompt")
        child.expect("> echo 'test'")
        print("found prompt, confirming")
        child.send("\n")
        print("sent newline, waiting to complete")
        child.read()
        child.close()
    finally:
        print("output")
        print("=====================================")
        # find the last non-empty line
        last_line = 0
        for i, line in enumerate(screen.display):
            if line.strip():
                last_line = i
        for line in screen.display[: last_line + 1]:
            print(line)
        print("=====================================")
    assert child.exitstatus == 0
    assert screen.display[last_line].strip() == "test"


if __name__ == "__main__":
    simple()
