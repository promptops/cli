
import Levenshtein
import requests

from promptops import user, settings
from promptops import trace

from promptops.ui.vim import edit_with_vim

from promptops.ui.input import non_empty_input

from promptops.query.suggest_next import SuffixTree
from promptops.ui import selections


def filter_similar(items):
    strings = [" ".join(item) for item in items]
    unique_strings = []
    unique_items = []

    for i, string1 in enumerate(strings):
        unique = True
        for string2 in unique_strings:
            if Levenshtein.jaro_winkler(string1, string2) > 0.75:
                unique = False
                break
        if unique:
            unique_strings.append(string1)
            unique_items.append(items[i])

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


def handle_detected_recipe(item):
    print("\nDetected Recipe:")
    print_steps(item)
    hashed = hash("".join(item))

    options = ["skip", "edit recipe", "save"]

    ui = selections.UI(options, is_loading=False)
    selection = ui.input()
    while selection != 2:
        if selection == 1:
            edit(item)
        else:
            return None
        ui = selections.UI(options, is_loading=False)
        selection = ui.input()

    print()
    # name = non_empty_input("Enter a name for the saved recipe: ")
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


def detect_recipes():
    suffix_tree = SuffixTree(5, 10000)
    detected = suffix_tree.find_repeated_sequences()
    detected = filter_similar(detected)[:4]
    print(f"We detected {len(detected)} possible recipes")

    print("When editing a recipe, insert or replace a value with <parameter-name> to create a parameter.")

    # todo: filter out recipes that have already been created
    # base 64 / hash somehow?

    recipes = []
    for item in detected:
        try:
            maybe_recipe = handle_detected_recipe(item)
            if maybe_recipe:
                recipes.append(maybe_recipe)
        except KeyboardInterrupt:
            return

    save_workflows(recipes)

