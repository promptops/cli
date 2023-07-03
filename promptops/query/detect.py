import hashlib

import requests

from promptops import user, settings
from promptops import trace

from promptops.ui.vim import edit_with_vim

from promptops.query.suggest_next import SuffixTree
from promptops.ui import selections
import shlex
from thefuzz import fuzz


def hash_it(item):
    string = " && ".join([i.strip() for i in item])
    return hashlib.sha256(string.encode('utf-8')).hexdigest()


def similarity(item1, item2):
    string1 = " && ".join(sorted(item1)).strip()
    string2 = " && ".join(sorted(item2)).strip()
    tokens1 = shlex.split(string1)
    tokens2 = shlex.split(string2)
    if tokens1[0] != tokens2[0]:
        return 0
    return fuzz.ratio(sorted(tokens1[1:]), sorted(tokens2[1:])) / 100.0


def filter_similar(items):
    response = requests.post(
        settings.endpoint + "/workflows/hashes",
        json={'trace_id': trace.trace_id},
        headers={"user-agent": f"promptops-cli; user_id={user.user_id()}"}
    )

    if response.status_code != 200:
        print("error", response.json())
        raise Exception(f"there was problem with the response, status: {response.status_code}")

    existing_hashes = response.json().get("hashes", [])
    unique_items = []

    for i, item in enumerate(items):
        if hash_it(item) in existing_hashes:
            continue

        unique = True
        for item2 in unique_items:
            if similarity(item, item2) > 0.75:
                unique = False
                break
        if unique:
            unique_items.append(item)

    unique_items = filter(lambda x: not all([i == x[0] for i in x]), unique_items)

    return list(unique_items)


def print_steps(item):
    for i, txt in enumerate(item):
        print(f'{i + 1}. {txt}')
    print()


def edit(steps):
    print()
    options = ["edit in vim", "clarify", "continue"]
    selection = None
    while selection != 2:
        ui = selections.UI(options, is_loading=False)
        selection = ui.input()
        print()
        if selection == 0:
            content = edit_with_vim("\n".join(steps))
            steps = [line for line in content.split("\n") if line.strip() != ""]
            print_steps(steps)
        else:
            print("TODO")
            pass


def handle_detected_workflow(item):
    print("\nDetected Workflow:")
    item = list(set(item))
    print_steps(item)
    hashed = hash_it(item)

    options = ["save", "skip", "edit"]
    ui = selections.UI(options, is_loading=False)
    selection = ui.input()
    while selection != 0:
        if selection == 2:
            edit(item)
        else:
            return None
        ui = selections.UI(options, is_loading=False)
        selection = ui.input()

    print()
    return {
        'commands': item,
        'hash': hashed
    }


def save_workflows(workflows):
    req = {
        'items': workflows,
        'trace_id': trace.trace_id,
    }

    response = requests.post(
        settings.endpoint + "/workflows",
        json=req,
        headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
        }
    )

    if response.status_code != 200:
        print("error", response.json())
        raise Exception(f"there was problem with the response, status: {response.status_code}")


def detect_workflows():
    suffix_tree = SuffixTree(5, 10000)
    detected = suffix_tree.find_repeated_sequences()
    detected = filter_similar(detected)
    print(f"We detected {len(detected)} possible workflows")

    workflows = []
    for item in detected:
        try:
            maybe_recipe = handle_detected_workflow(item)
            if maybe_recipe:
                workflows.append(maybe_recipe)
        except KeyboardInterrupt:
            if len(workflows) == 0:
                return

            print("Do you want to save the selections you have made so far?\n")
            options = ["save", "exit"]
            ui = selections.UI(options, is_loading=False)
            selection = ui.input()
            if selection == 0:
                save_workflows(workflows)
            return

    save_workflows(workflows)

