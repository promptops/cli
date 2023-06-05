import os
import subprocess
from typing import Optional

import requests
import sys

from promptops import settings
from promptops import trace
from promptops import user
from promptops.feedback import feedback
from promptops.loading import loading_animation, Simple
from promptops.recipes.terraform import TerraformExecutor
from promptops.ui import selections
from promptops.ui.input import non_empty_input
from promptops.ui.vim import edit_with_vim

LANG_SHELL = 'shell'
LANG_TF = 'terraform'
LANG_OPTIONS = [LANG_TF, LANG_SHELL]


def regenerate_recipe_execution(recipe, clarification):
    req = {
        "trace_id": trace.trace_id,
        "id": recipe['id'],
        "clarification": clarification
    }

    response = requests.post(
        settings.endpoint + "/recipe/regenerate",
        json=req,
        headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
        },
    )
    if response.status_code != 200:
        print(response.json())
        raise Exception(f"there was problem with the response, status: {response.status_code}")

    return response.json()


def get_recipe_execution(recipe: dict):
    req = {
        "trace_id": trace.trace_id,
        "id": recipe['id'],
    }

    response = requests.post(
        settings.endpoint + "/recipe/execution",
        json=req,
        headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
        },
    )
    if response.status_code != 200:
        raise Exception(f"there was problem with the response, status: {response.status_code}")

    return response.json()


def clarify_steps(recipe, clarification):
    req = {
        "id": recipe['id'],
        "trace_id": trace.trace_id,
        "clarification": clarification,
    }

    response = requests.post(
        settings.endpoint + "/recipe/clarify",
        json=req,
        headers={"user-agent": f"promptops-cli; user_id={user.user_id()}"}
    )

    if response.status_code != 200:
        raise Exception(f"there was problem with the response, status: {response.status_code}")

    return response.json()


def init_recipe(prompt: str, language: str, workflow_id=None):
    req = {
        "prompt": prompt,
        "trace_id": trace.trace_id,
        "platform": sys.platform,
        "language": language,
        "author": user.user_id(),
        "recipe_id": workflow_id,
    }

    if language == LANG_SHELL:
        req['shell'] = os.environ.get("SHELL")

    response = requests.post(
        settings.endpoint + "/recipe/init",
        json=req,
        headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
        }
    )

    if response.status_code != 200:
        raise Exception(f"there was problem with the response, status: {response.status_code}")

    return response.json()


def run(script: str, lang: str = "shell") -> (int, Optional[str]):
    if lang == "shell":
        proc = subprocess.run(
            script, shell=True, start_new_session=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if proc.stdout and str(proc.stdout) != "":
            sys.stdout.write(proc.stdout.decode("utf-8"))
        if proc.stderr and str(proc.stderr) != "":
            sys.stdout.write(proc.stderr.decode("utf-8"))
        sys.stdout.flush()

        return proc.returncode, str(proc.stderr)
    else:
        raise NotImplementedError(f"{lang} not implemented yet")


def print_steps(steps):
    for i, step in enumerate(steps):
        print(f"{i + 1}. {step}")
    print()


def edit_steps(recipe):
    steps = recipe.get('steps', [])
    og = steps
    print("Based on your requirements, I've set the project outline to include the following steps ")
    print_steps(steps)

    options = ["edit in vim", "clarify", "continue"]
    selection = None
    while selection != 2:
        ui = selections.UI(options, is_loading=False)
        selection = ui.input()
        print()
        if selection == 0:
            edited = edit_with_vim("\n".join(steps))
            recipe['steps'] = edited.split("\n")
            steps = recipe['steps']
            print_steps(steps)
        elif selection == 1:
            print()
            clarification = input("add details: ").strip()
            with loading_animation(Simple("weaving in your clarification...")):
                recipe = clarify_steps(recipe, clarification)
            steps = recipe.get('steps')
            print()
            print("Based on your requirements & clarification, I've set the project outline to include the following steps ")
            print_steps(steps)

    if og != recipe.get('steps'):
        save_steps(recipe)

    return recipe


def save_steps(recipe):
    print()
    req = {
        'id': recipe.get('id'),
        'trace_id': trace.trace_id,
        'steps': recipe.get('steps')
    }

    response = requests.post(
        settings.endpoint + "/recipe/steps",
        json=req,
        headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
        }
    )

    if response.status_code != 200:
        print("error", response.json())
        raise Exception(f"there was problem with the response, status: {response.status_code}")


def save_flow(recipe):
    print()
    req = {
        'id': recipe.get('id'),
        'trace_id': trace.trace_id,
        'name': non_empty_input("Enter a name for the saved workflow: "),
        'description': non_empty_input("Enter a brief description: "),
        'parameters': recipe.get('parameters'),
        'execution': recipe.get('execution')
    }

    response = requests.post(
        settings.endpoint + "/recipe/save",
        json=req,
        headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
        }
    )

    if response.status_code != 200:
        print("error", response.json())
        raise Exception(f"there was problem with the response, status: {response.status_code}")


def list_workflows():
    response = requests.get(settings.endpoint + f"/recipe?trace_id={trace.trace_id}", headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
    })

    if response.status_code != 200:
        print("error", response.json(), "code", response.status_code)
        raise Exception(f"there was problem with the response, status: {response.status_code}")

    return response.json().get('recipes', [])


def available_workflows():
    recipes = list_workflows()
    if not recipes or len(recipes) == 0:
        print("You don't have any saved workflows. To create a workflow try 'um workflow prompt'")
        return None

    print("Available Workflows")
    names = [p.get('name') for p in recipes]
    selected = None
    while not selected:
        ui = selections.UI(names, is_loading=False)
        recipe_selection = ui.input()
        print()

        selection = 1
        while selection == 1:
            ui = selections.UI(['select', 'describe', 'go back'], is_loading=False)
            selection = ui.input()
            if selection == 0:
                selected = recipes[recipe_selection]
                print()
            elif selection == 1:
                print()
                describe = recipes[recipe_selection]
                print(f"Description: {describe.get('description')} - {describe.get('language')}")
    return selected


def workflow_entrypoint(args):
    new_recipe = True
    if not args or len(args.question) < 1:
        new_recipe = False
        recipe = available_workflows()
        if not recipe:
            return
        recipe = init_recipe(recipe['prompt'], recipe['language'], recipe['id'])
    else:
        prompt = " ".join(args.question)

        print("Workflows are currently based on Terraform. Support for more methods coming soon.\n")
        # ui = selections.UI(LANG_OPTIONS, is_loading=False)
        # selection = ui.input()
        # print()
        selection = 0

        with loading_animation(Simple("getting an outline ready...")):
            recipe = init_recipe(prompt, LANG_OPTIONS[selection])
        recipe = edit_steps(recipe)

        with loading_animation(Simple("processing instructions...")):
            recipe = get_recipe_execution(recipe)

    print("Great! We are just about ready to run, just a few more questions: ")
    executor = TerraformExecutor(recipe)
    result = executor.run(regen=regenerate_recipe_execution)
    feedback({"event": "recipe-execute", "id": recipe.get('id'), "result": result})

    if new_recipe:
        print()
        print("Would you like to save this as a reusable workflow?")
        print()
        ui = selections.UI(["save", "exit"], is_loading=False)
        selection = ui.input()
        if selection == 0:
            save_flow(recipe)
            print()
            print("To use this workflow, simply type 'um workflow' without any prompt")
        print()
