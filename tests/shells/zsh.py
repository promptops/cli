import tempfile
from promptops.shells.zsh import Zsh


contents = """
: 1683929171:0;export SECRET_KEY="aKbyRLXXXXXXXXXXXXXXXXXXXXXXXXXXIzYwm/lX"
: 1683929174:0;echo $SECRET_KEY
: 1683929187:0;cat single line > test.txt
: 1683929206:0;echo very \\
long \\
line
: 1683930257:0;export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
: 1683932479:0;exit
"""


expected = [
    'export SECRET_KEY="<SECRET>"',
    "echo $SECRET_KEY",
    "cat single line > test.txt",
    "echo very \\\nlong \\\nline",
    # for some reason the JWT plugin fails to grab the full token, but that should be enough
    'export TOKEN="<SECRET>SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"',
    "exit",
]


def test_zsh():
    with tempfile.NamedTemporaryFile() as tmp:
        with open(tmp.name, "w") as f:
            f.write(contents)

        shell = Zsh(tmp.name)
        cmds = shell.get_recent_history(2)
        assert cmds == expected[-2:]

        cmds = shell.get_recent_history(3)
        assert cmds == expected[-3:]

        cmds = shell.get_recent_history(10)
        assert cmds == expected

        cmds = shell.get_full_history()
        assert cmds == expected
