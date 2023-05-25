from promptops.query.query import run
from promptops.query.dtos import Result


def test_run():
    script = "echo 'test'"
    rc, stderr = run(Result(script=script))
    assert rc == 0
    assert stderr == ""


def test_run_fail():
    script = "echo 'test' && exit 1"
    rc, stderr = run(Result(script=script))
    assert rc == 1
    assert stderr == ""


def test_run_fail_stderr():
    script = "echo 'test' >&2 && exit 1"
    rc, stderr = run(Result(script=script))
    assert rc == 1
    assert stderr == "test\n"


def check_stream():
    script = "echo 1 && sleep 1 && echo 2"
    rc, stderr = run(Result(script=script))
    assert rc == 0
    assert stderr == ""


if __name__ == "__main__":
    check_stream()
