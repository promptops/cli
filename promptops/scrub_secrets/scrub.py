from detect_secrets import SecretsCollection
from detect_secrets.settings import default_settings


def scrub_file(filename, lines):
    secrets = SecretsCollection()
    lines_to_secrets = {}

    with default_settings():
        secrets.scan_file(filename)
        for secret in secrets.data[filename]:
            if lines_to_secrets.get(secret.line_number - 1) is None:
                lines_to_secrets[secret.line_number - 1] = [secret]
            else:
                lines_to_secrets[secret.line_number - 1].append(secret)

    for index, secrets in lines_to_secrets.items():
        for secret in secrets:
            lines[index] = lines[index].replace(secret.secret_value, "<SECRET>")

    return lines


def scan_lines(fake_filename: str, lines: list[str]):
    from detect_secrets.settings import get_plugins
    from detect_secrets.core.scan import _scan_line, _is_filtered_out
    from detect_secrets.util.code_snippet import get_code_snippet

    for line_number, line in enumerate(lines, start=1):
        code_snippet = get_code_snippet(lines, line_number)

        yield from (
            secret
            for plugin in get_plugins()
            for secret in _scan_line(
                plugin=plugin,
                filename=fake_filename,
                line=line,
                line_number=line_number,
                context=code_snippet,
            )
            if not _is_filtered_out(
                required_filter_parameters=["context"],
                filename=secret.filename,
                secret=secret.secret_value,
                plugin=plugin,
                line=line,
                context=code_snippet,
            )
        )


_PADDING = [
    "echo hello world",
    "cat test > test.txt",
    'git commit -m "um: padding for secrets"',
    "git pull --rebase",
    "git push",
]


def scrub_lines(fake_filename: str, lines: list[str]) -> list[str]:
    # copy the lines, we'll update in place
    scrubbed = [line for line in lines]
    with default_settings():
        for secret in scan_lines(fake_filename, _PADDING + lines + _PADDING):
            i = secret.line_number - 1 - len(_PADDING)
            if i < 0 or i > len(lines):
                continue
            scrubbed[i] = lines[i].replace(secret.secret_value, "<SECRET>")
    return scrubbed


def scrub_line(fake_filename: str, line: str) -> str:
    return scrub_lines(fake_filename, [line])[0]
