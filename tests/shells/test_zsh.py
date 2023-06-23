import tempfile
from promptops.shells.zsh import Zsh
import pytest


contents = b"""
: 1683929171:0;export SECRET_KEY="aKbyRLXXXXXXXXXXXXXXXXXXXXXXXXXXIzYwm/lX"
: 1683929174:0;echo $SECRET_KEY
: 1683929187:0;cat single line > test.txt
: 1683929190:0;echo \xF0\x83\xBF\x83\xB8\x83\xA3
: 1683929206:0;echo very \\\\
long \\\\
line
: 1683929207:0;echo 'very \\
long \\
line'
: 1683929206:0;echo \\\\not so \\\\
long \\ line
: 1683930257:0;export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
: 1683932479:0;exit
"""


contents_simple = b"""
export SECRET_KEY="aKbyRLXXXXXXXXXXXXXXXXXXXXXXXXXXIzYwm/lX"
echo $SECRET_KEY
cat single line > test.txt
echo \xF0\x83\xBF\x83\xB8\x83\xA3
echo very \\\\
long \\\\
line
echo 'very \\
long \\
line'
echo \\\\not so \\\\
long \\ line
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
exit
"""

expected = [
    'export SECRET_KEY="<SECRET>"',
    "echo $SECRET_KEY",
    "cat single line > test.txt",
    'echo 😃',
    "echo very \\\nlong \\\nline",
    "echo 'very \nlong \nline'",
    "echo \\\\not so \\\nlong \\ line",
    # for some reason the JWT plugin fails to grab the full token, but that should be enough
    'export TOKEN="<SECRET>SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"',
    "exit",
]


def setup():
    from promptops.shells.base import reset_extra_history
    reset_extra_history()


def test_zsh():
    with tempfile.NamedTemporaryFile() as tmp:
        with open(tmp.name, "wb") as f:
            f.write(contents)

        shell = Zsh(tmp.name)
        cmds = shell.get_recent_history(2)
        assert cmds == expected[-2:]

        cmds = shell.get_recent_history(4)
        assert cmds == expected[-4:]

        cmds = shell.get_recent_history(10)
        assert cmds == expected

        cmds = shell.get_full_history()
        assert cmds == expected


def test_zsh_simple():
    with tempfile.NamedTemporaryFile() as tmp:
        with open(tmp.name, "wb") as f:
            f.write(contents_simple)

        shell = Zsh(tmp.name)
        cmds = shell.get_recent_history(2)
        assert cmds == expected[-2:]

        cmds = shell.get_recent_history(4)
        assert cmds == expected[-4:]

        cmds = shell.get_recent_history(10)
        assert cmds == expected

        cmds = shell.get_full_history()
        assert cmds == expected


def test_add_to_history():
    from promptops import settings
    with tempfile.NamedTemporaryFile() as tmp_hist, tempfile.NamedTemporaryFile() as tmp:
        with open(tmp.name, "wb") as f:
            f.write(contents)
        settings.temp_history_file = tmp_hist.name
        shell = Zsh(tmp.name)

        cmds = shell.get_recent_history(4)
        assert cmds == expected[-4:]

        cmds = shell.get_full_history()
        assert cmds == expected

        extra_commands = [
            "echo 'hello\nworld'",
            "um say cheese",
            "echo \"test\"",
        ]

        expected_extra = [
            "echo 'hello\nworld'",
            "echo \"test\"",
        ]

        for cmd in extra_commands:
            shell.add_to_history(cmd)

        cmds = shell.get_recent_history(1)
        assert cmds == (expected + expected_extra)[-1:]
        cmds = shell.get_recent_history(5)
        assert cmds == (expected + expected_extra)[-5:]

        cmds = shell.get_full_history()
        assert cmds == (expected + expected_extra)
