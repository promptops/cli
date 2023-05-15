from promptops.query.query import run
from promptops.query.dtos import Result
import subprocess


def test_run():
    script = "ls -l"
    rc = run(Result(script=script))
    assert rc == 0
