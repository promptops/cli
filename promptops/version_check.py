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

    @staticmethod
    def from_dict(data: dict) -> "Response":
        return Response(
            update_required=data.get("update_required", False),
            message=data.get("message"),
            latest_version=data.get("latest_version"),
        )


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
    if r.update_required:
        print()
        print_formatted_text(HTML("    <bold>update is required</bold>"))
        print_formatted_text(
            HTML(
                f"    current version: <ansired>{version.__version__}</ansired>, latest: <ansigreen>{r.latest_version}</ansigreen>"
            )
        )
        message = "to update run <ansigreen>pip install --upgrade git+https://github.com/promptops/cli.git</ansigreen>"
        print_formatted_text(HTML(f"    {r.message or message}"))
        print()
    return r
