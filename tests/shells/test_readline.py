from promptops.shells.base import reverse_readline, readline
import tempfile


def test_reverse_readline():
    contents = """hello world
line with emoji 🤔 and unicode ⬢⬡⬢
another line
third line"""
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


def test_readline():
    contents = """hello world
line with emoji 🤔 and unicode ⬢⬡⬢
another line
third line"""
    expected = list(contents.splitlines())
    with tempfile.NamedTemporaryFile(mode="w") as f:
        f.write(contents)
        f.flush()
        lines = list(readline(f.name, 1024))
        assert lines == expected
        lines = list(readline(f.name, 16))
        assert lines == expected
        lines = list(readline(f.name, 1))
        assert lines == expected


def test_simple_reverse():
    contents = "1\n2"
    expected = list(reversed(contents.splitlines()))
    with tempfile.NamedTemporaryFile(mode="w") as f:
        f.write(contents)
        f.flush()
        lines = list(reverse_readline(f.name, 1))
        assert lines == expected
        lines = list(reverse_readline(f.name, 2))
        assert lines == expected
