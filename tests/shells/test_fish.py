import tempfile
from promptops.shells.fish import Fish


contents = """
- cmd: export SECRET_KEY="aKbyRLXXXXXXXXXXXXXXXXXXXXXXXXXXIzYwm/lX"
  when: 1683929171
- cmd: echo $SECRET_KEY
  when: 1683929174
- cmd: cat single line > test.txt
  when: 1683929187
- cmd: echo 'some\\nmulti-line\\ntext'
  when: 1684894201
- cmd: echo hello\\\\ world
  when: 1684894222
- cmd: echo hello \\\\\\nworld
  when: 1684896972
- cmd: . venv/bin/activate.fish
  when: 1684897584
  paths:
    - venv/bin/activate.fish
- cmd: echo 😃
  when: 1685039307
- cmd: export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
  when: 1685039308
- cmd: exit
  when: 1685039328
"""


expected = [
    'export SECRET_KEY="<SECRET>"',
    "echo $SECRET_KEY",
    "cat single line > test.txt",
    "echo 'some\nmulti-line\ntext'",
    "echo hello\\ world",
    "echo hello \\\nworld",
    ". venv/bin/activate.fish",
    'echo 😃',
    # for some reason the JWT plugin fails to grab the full token, but that should be enough
    'export TOKEN="<SECRET>SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"',
    "exit",
]


def test_recent():
    with tempfile.NamedTemporaryFile() as tmp:
        with open(tmp.name, "w") as f:
            f.write(contents)

        shell = Fish(tmp.name)
        cmds = shell.get_recent_history(2)
        assert cmds == expected[-2:]

        cmds = shell.get_recent_history(4)
        assert cmds == expected[-4:]

        cmds = shell.get_recent_history(10)
        assert cmds == expected


def test_full():
    with tempfile.NamedTemporaryFile() as tmp:
        with open(tmp.name, "w") as f:
            f.write(contents)

        shell = Fish(tmp.name)
        cmds = shell.get_full_history()
        assert cmds == expected
