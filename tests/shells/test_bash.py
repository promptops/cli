import tempfile
from promptops.shells.bash import Bash


contents = """
export SECRET_KEY="aKbyRLXXXXXXXXXXXXXXXXXXXXXXXXXXIzYwm/lX"
echo $SECRET_KEY
cat single line > test.txt
echo very long line
echo 'very
long
line'
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
exit
"""


expected = [
    'export SECRET_KEY="<SECRET>"',
    "echo $SECRET_KEY",
    "cat single line > test.txt",
    "echo very long line",
    "echo 'very\nlong\nline'",
    # for some reason the JWT plugin fails to grab the full token, but that should be enough
    'export TOKEN="<SECRET>SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"',
    "exit",
]


def test_bash():
    with tempfile.NamedTemporaryFile() as tmp:
        with open(tmp.name, "w") as f:
            f.write(contents)

        shell = Bash(tmp.name)
        cmds = shell.get_recent_history(2)
        assert cmds == expected[-2:]

        cmds = shell.get_recent_history(4)
        assert cmds == expected[-4:]

        cmds = shell.get_recent_history(10)
        assert cmds == expected

        cmds = shell.get_full_history()
        assert cmds == expected
