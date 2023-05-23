import sys
from typing import Optional

from promptops import settings
import os
import uuid
from functools import lru_cache
from promptops.ui.prompts import confirm, EXIT, GO_BACK
from promptops.ui import selections
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import HTML
import requests
from promptops.trace import trace_id
from promptops.settings_store import save, set_index_history


@lru_cache(maxsize=1)
def user_id() -> str:
    real_path = os.path.expanduser(settings.user_id_path)
    if not os.path.exists(real_path):
        uid = f"user-{uuid.uuid4().hex}"
        os.makedirs(os.path.dirname(real_path), exist_ok=True)
        with open(real_path, "w") as f:
            f.write(uid)
        return uid
    with open(real_path) as f:
        return f.read().strip()


def user_agent() -> str:
    return f"promptops-cli; user_id={user_id()}"


def has_registered() -> bool:
    real_path = os.path.expanduser(settings.user_id_path)
    return os.path.exists(real_path)


def config_flow() -> Optional[dict]:
    config_selections = {}

    print()
    print_formatted_text(
        HTML("  👋 thanks for installing <ansigreen><b>um</b></ansigreen>! let's make sure you get the most out of it")
    )
    print()

    options = ["continue", "skip"]
    ui = selections.UI(options, is_loading=False)
    selection = ui.input()
    if selection == 1:
        return

    print()
    print()
    print("  📖 indexing your history can greatly improve the speed and the quality of the suggestions")
    print_formatted_text(
        HTML(
            "  do you want to index your history? <b><i>we take special care to"
            " scrub secrets before indexing</i></b>"
        )
    )
    print()

    options = ["confirm", "skip"]
    ui = selections.UI(options, is_loading=False)
    selection = ui.input()
    if selection != 1:
        from promptops.history import index_history

        set_index_history(True)
        index_history(show_progress=True)
        config_selections["loaded_history"] = True

    print()
    while True:
        print()
        context_size = 2
        print(
            f"  ↩️  say more with less! the number of previous commands to include"
            f" in the query context (default: {context_size})?"
        )
        print()
        options = ["confirm defaults", "change"]
        ui = selections.UI(options, is_loading=False)
        selection = ui.input()
        if selection == 0:
            from promptops.settings_store import set_history_context

            set_history_context(context_size)
            config_selections["context_size"] = context_size
            break
        else:
            while True:
                choice = confirm(str(context_size)).strip()
                if choice == GO_BACK:
                    break
                if choice == EXIT:
                    return
                if choice.isdigit():
                    # TODO: validate
                    break
            if choice == GO_BACK:
                continue
            from promptops.settings_store import set_history_context

            set_history_context(int(choice))
            config_selections["context_size"] = int(choice)
            break

    print()
    print("  🎉 all done! 🎉")
    print()

    return config_selections


def register():
    print()
    print("  📢 provide your email address to receive occasional updates and tips (optional, leave blank to skip)")
    email = confirm("").strip()
    if email in [GO_BACK, EXIT]:
        email = ""
    print()

    requests.post(
        settings.endpoint + "/installed",
        json={"trace_id": trace_id, "email": email, "platform": sys.platform, "python_version": sys.version},
        headers={"user-agent": user_agent()},
    )
    config = config_flow()
    config["trace_id"] = trace_id
    requests.post(settings.endpoint + "/config", json=config, headers={"user-agent": user_agent()})
    save()
