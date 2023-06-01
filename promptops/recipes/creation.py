import os
import subprocess
from typing import Optional, List

import requests
import sys

from promptops import settings
from promptops import trace
from promptops import user
from promptops.loading import loading_animation, Simple
from promptops.recipes.terraform import TerraformExecutor
from promptops.ui import selections
from promptops.ui.vim import edit_with_vim

LANG_SHELL = 'shell'
LANG_TF = 'terraform'
LANG_OPTIONS = [LANG_TF, LANG_SHELL]


def regenerate_recipe_execution(recipe, clarification):
    req = {
        "trace_id": trace.trace_id,
        "id": recipe['id'],
        "parameters": recipe['parameters'],
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

    data = response.json()

    if not data.get("steps"):
        raise Exception(f"missing steps")

    return data


def get_recipe_execution(recipe: dict, language: str):
    req = {
        "trace_id": trace.trace_id,
        "id": recipe['id'],
        "parameters": recipe['parameters'],
    }
    if language == LANG_SHELL:
        req['shell'] = os.environ.get('SHELL')
    else:
        req['language'] = language

    response = requests.post(
        settings.endpoint + "/recipe/execution",
        json=req,
        headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
        },
    )
    if response.status_code != 200:
        print(response.json())
        raise Exception(f"there was problem with the response, status: {response.status_code}")

    data = response.json()

    if not data.get("steps"):
        raise Exception(f"missing steps")

    return data


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

    data = response.json()

    if not data.get("steps"):
        raise Exception(f"missing steps")

    return data


def init_recipe(prompt: str, language: str):
    req = {
        "prompt": prompt,
        "trace_id": trace.trace_id,
        "platform": sys.platform,
        "language": language,
        "author": user.user_id(),
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

    data = response.json()

    if not data.get("steps"):
        raise Exception(f"missing steps")

    return data


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
    print("Based on your requirements, I've set the project outline to include the following steps ")

    print_steps(steps)

    options = ["edit in vim", "clarify", "continue"]
    selection = None
    while selection != 2:
        ui = selections.UI(options, is_loading=False)
        selection = ui.input()
        if selection == 0:
            edited = edit_with_vim("\n".join(steps))
            recipe['steps'] = edited.split("\n")
            steps = recipe['steps']
            print_steps(steps)

            # TODO: Save the edited steps through the API
        elif selection == 1:
            print()
            clarification = input("add details: ").strip()
            with loading_animation(Simple("weaving in your clarification...")):
                recipe = clarify_steps(recipe, clarification)
            steps = recipe.get('steps')
            print("Based on your requirements & clarification, I've set the project outline to include the following steps ")
            print_steps(steps)

    # parameters = recipe.get('parameters', [])

    # TODO: Remove this, move "user friendly" questions over to tf generator
    # for parameter in parameters:
    #     question = parameter.get('description')
    #     if parameter.get("options"):
    #         print(question)
    #         ui = selections.UI(parameter.get('options'), is_loading=False)
    #         selection = ui.input()
    #         value = parameter.get('options')[selection]
    #     else:
    #         value = input(f"{question}: ")
    #     parameter['value'] = value

    return recipe


def workflow_entrypoint(args):
    if not args.question or len(args.question) < 1:
        print("you must include a question")
        return
    prompt = " ".join(args.question)

    print("choose a method to execute this workflow\n")
    ui = selections.UI(LANG_OPTIONS, is_loading=False)
    selection = ui.input()
    print()

    with loading_animation(Simple("getting an outline ready...")):
        recipe = init_recipe(prompt, LANG_OPTIONS[selection])
    recipe = edit_steps(recipe)

    with loading_animation(Simple("processing instructions...")):
        recipe = get_recipe_execution(recipe, LANG_OPTIONS[selection])

    executor = TerraformExecutor(recipe, input("enter a relative directory to store the terraform in: "))
    executor.run(regen=regenerate_recipe_execution)
    return
