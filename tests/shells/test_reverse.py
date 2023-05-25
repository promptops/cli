from promptops.shells.base import reverse_readline
import tempfile


def test_reverse_readline():
    contents = """hello world
line with emoji 🤔 and unicode ⬢⬡⬢
another line
third line
"""
    expected = list(reversed(contents.splitlines()))
    with tempfile.NamedTemporaryFile(mode="w") as f:
        f.write(contents)
        f.flush()
        lines = list(reverse_readline(f.name, 1024))
        assert lines == expected
        lines = list(reverse_readline(f.name, 16))
        assert lines == expected
        lines = list(reverse_readline(f.name, 1))
        assert lines == expected
