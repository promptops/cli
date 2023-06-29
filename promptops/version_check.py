import os.path
import time

import requests
from promptops import settings
from promptops import user
from promptops import version
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import HTML
from dataclasses import dataclass
from promptops.trace import trace_id


@dataclass
class Response:
    update_required: bool = False
    message: str = None
    latest_version: str = None
    changes: list[dict] = None

    @staticmethod
    def from_dict(data: dict) -> "Response":
        return Response(
            update_required=data.get("update_required", False),
            message=data.get("message"),
            latest_version=data.get("latest_version"),
            changes=data.get("changes"),
        )


def should_show_changes(r: Response):
    if r.update_required:
        return True
    filename = os.path.expanduser(settings.version_check_file)
    if os.path.exists(filename):
        try:
            with open(filename) as f:
                if f.read() != r.latest_version:
                    return True
            # check if the file is older according to settings.show_changes_frequency
            if time.time() - os.path.getmtime(filename) > settings.show_changes_frequency:
                return True
        except OSError:
            return True
        return False
    else:
        return True


def version_check():
    response = requests.post(
        settings.endpoint + "/version",
        json={
            "version": version.__version__,
            "trace_id": trace_id,
        },
        headers={"user-agent": f"promptops-cli; user_id={user.user_id()}"},
    )
    if response.status_code != 200:
        print("version check failed", response.status_code, response.text)
    data = response.json()
    r = Response.from_dict(data)

    if should_show_changes(r):
        if r.changes:
            print(f"  📢 Version {r.latest_version} is now available! Changes since version {version.__version__}:")
            print()
            for change in r.changes:
                print_formatted_text(HTML(f"    <underline>version {change['version']}</underline>"))
                for c in change["changes"]:
                    print_formatted_text(HTML(f"    ● {c}"))
                print()
        try:
            with open(os.path.expanduser(settings.version_check_file), "w") as f:
                f.write(r.latest_version)
        except OSError as e:
            from promptops.feedback import feedback
            feedback({"event": "handled_exception", "message": str(e), "location": "write version check file"})
    if r.update_required:
        print()
        print_formatted_text(HTML("    <bold>update is required</bold>"))
        print_formatted_text(
            HTML(
                f"    current version: <ansired>{version.__version__}</ansired>, latest: <ansigreen>{r.latest_version}</ansigreen>"
            )
        )
        message = "to update run <ansigreen>pip install --upgrade promptops</ansigreen>"
        print_formatted_text(HTML(f"    {r.message or message}"))
        print()

    return r
