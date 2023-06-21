import json
import logging
import os
import queue
import subprocess
import time

import colorama
import requests
import sys

from typing import Optional
from promptops import settings
from promptops import trace
from promptops import user
from promptops.feedback import feedback
from promptops.loading.cancellable import CancellableMultiLoader, CancellableSimpleLoader
from promptops.recipes.terraform import TerraformExecutor
from promptops.ui import selections
from promptops.ui.input import non_empty_input
from promptops.ui.prompts import confirm, GO_BACK
from promptops.ui.vim import edit_with_vim

LANG_SHELL = 'shell'
LANG_TF = 'terraform'
LANG_OPTIONS = [LANG_TF, LANG_SHELL]


class StreamException(Exception):
    pass



def handle_execution_response(recipe, response, loading):
    completed_queue = queue.Queue()
    started_queue = queue.Queue()
    file_loader = None
    loading_parameters = False
    for line in response.iter_lines():
        if line:
            json_line = json.loads(line.decode('utf-8'))
            if json_line.get('type') == 'files':
                loading.stop()
                file_loader = CancellableMultiLoader(started_queue, completed_queue)
                for file in json_line.get('files'):
                    started_queue.put(file)
            elif json_line.get('type') == 'execution':
                if not loading_parameters:
                    completed_queue.put('gathering parameters')
                    loading_parameters = False
                recipe.setdefault('execution', []).append(json_line)
                completed_queue.put(json_line.get('key'))
            elif json_line.get('parameter'):
                if not loading_parameters:
                    started_queue.put('gathering parameters')
                    loading_parameters = True
                recipe.setdefault('parameters', []).append(json_line)
            elif json_line.get('error'):
                raise StreamException
            else:
                logging.debug('unknown json object', json_line)

    if file_loader:
        file_loader.stop()
    return recipe


def regenerate_recipe_execution(recipe, clarification, error=None, loading=None):
    req = {
        "trace_id": trace.trace_id,
        "id": recipe['id'],
        "clarification": clarification,
    }

    if error:
        req['error'] = error

    response = requests.post(
        settings.endpoint + "/recipe/stream/regenerate",
        json=req,
        headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
        },
        stream=True
    )
    recipe['execution'] = []
    recipe['parameters'] = []

    return handle_execution_response(recipe, response, loading)


def get_recipe_execution(recipe: dict, loading=None):
    req = {
        "trace_id": trace.trace_id,
        "id": recipe['id'],
    }

    response = requests.post(
        settings.endpoint + "/recipe/stream/execution",
        json=req,
        headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
        },
        stream=True
    )

    recipe['execution'] = []
    recipe['parameters'] = []

    return handle_execution_response(recipe, response, loading)


def clarify_steps(recipe, clarification, loading=None):
    req = {
        "id": recipe['id'],
        "trace_id": trace.trace_id,
        "clarification": clarification,
    }

    response = requests.post(
        settings.endpoint + "/recipe/stream/clarify",
        json=req,
        headers={"user-agent": f"promptops-cli; user_id={user.user_id()}"},
        stream=True
    )

    recipe['steps'] = []
    count_minus = 0
    for line in response.iter_lines():
        if line:
            if loading:
                loading.stop()
            json_line = json.loads(line.decode('utf-8'))
            if json_line.get('id'):
                recipe['id'] = json_line.get('id')
            elif json_line.get('error'):
                raise StreamException
            elif json_line.get('step'):
                if len(recipe['steps']) == 0:
                    print("Based on your requirements & extra details, I've set the project outline to include the following steps: ")
                recipe['steps'].append(json_line.get('step'))
                prefix, step_num = json_line.get("prefix", ""), ""
                if prefix == " -- ":
                    prefix = colorama.Fore.RED + prefix + colorama.Style.RESET_ALL
                    count_minus += 1
                else:
                    prefix = colorama.Fore.GREEN + prefix + colorama.Style.RESET_ALL
                    step_num = str(len(recipe['steps']) - count_minus) + "."
                print(f'{prefix}{step_num} {json_line.get("step")}')
            if loading:
                loading.start()
            else:
                logging.debug("unsupported json item: ", line)

    if loading:
        loading.stop()
    print()

    return recipe


def init_recipe(prompt: str, language: str, workflow_id=None, loading=None):
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
        settings.endpoint + "/recipe/stream/init",
        json=req,
        headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
        },
        stream=True
    )

    recipe = {
        'steps': []
    }
    for line in response.iter_lines():
        if line:
            if loading:
                loading.stop()
            json_line = json.loads(line.decode('utf-8'))
            if json_line.get('id'):
                recipe['id'] = json_line.get('id')
            elif json_line.get('error'):
                raise StreamException
            elif json_line.get('step'):
                if len(recipe['steps']) == 0:
                    print("Based on your requirements, I've set the project outline to include the following steps: ")
                recipe['steps'].append(json_line.get('step'))
                print(f"{len(recipe['steps'])}. {json_line.get('step')}")
            if loading:
                loading.start()
    if loading:
        loading.stop()

    print()
    return recipe


def get_recipe(prompt: str, language: str, workflow_id=None):
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
        },
    )

    if response.status_code == 404:
        return print("recipe not found")
    elif response.status_code != 200:
        return print("an error occurred retrieving the recipe")

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
    print()

    options = ["edit in vim", "clarify", "continue"]
    selection = None
    while selection != 2:
        ui = selections.UI(options, is_loading=False)
        selection = ui.input()
        print()
        if selection == 0:
            edited = edit_with_vim("\n".join([s for s in steps if s.strip() != ""]))
            recipe['steps'] = edited.split("\n")
            steps = recipe['steps']
            print_steps(steps)
        elif selection == 1:
            clarification = input("add details: ").strip()
            recipe = clarify_steps(recipe, clarification, loading=CancellableSimpleLoader("getting an outline ready..."))

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


def edit_parameters(recipe):
    parameter_names = [p.get('parameter') for p in recipe.get('parameters')]
    options = parameter_names + ['exit']

    while True:
        print("Do you want to set defaults or modify any of the parameters?\n")

        ui = selections.UI(options, is_loading=False)
        selection = ui.input()

        if selection == len(options) - 1:
            break

        parameter = recipe.get('parameters')[selection]
        print(f"{parameter.get('name')}: {parameter.get('description')}")
        modify = ['set a default value', 'modify the question', 'go back']
        selection = None
        while selection != 2:
            print()
            ui = selections.UI(modify, is_loading=False)
            selection = ui.input()
            if selection == 0:
                parameter['default'] = non_empty_input('enter a default value: ')
            elif selection == 1:
                parameter['description'] = non_empty_input('enter a new question for the parameter: ')
    return recipe


def save_flow(recipe):
    print()
    recipe = edit_parameters(recipe)

    req = {
        'id': recipe.get('id'),
        'trace_id': trace.trace_id,
        'name': non_empty_input("Enter a name for the saved workflow: "),
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


def list_recipes():
    response = requests.get(settings.endpoint + f"/recipe?trace_id={trace.trace_id}", headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
    })

    if response.status_code != 200:
        print("error", response.json(), "code", response.status_code)
        raise Exception(f"there was problem with the response, status: {response.status_code}")

    return response.json().get('recipes', [])


def available_recipes():
    recipes = list_recipes()
    if not recipes or len(recipes) == 0:
        print("You don't have any saved recipes. To create a recipe try 'um recipe <prompt>'")
        return None

    print("Select from available recipes: ")
    names = [p.get('name') for p in recipes]
    selected = None
    while not selected:
        ui = selections.UI(names, is_loading=False)
        recipe_selection = ui.input()
        print()

        print(f"{names[recipe_selection]}: {recipes[recipe_selection].get('prompt')}")
        confirmed = confirm("Use this recipe?")
        if confirmed != GO_BACK:
            selected = recipes[recipe_selection]
        else:
            print("\nSelect from available recipes: ")
    return selected


def recipe_entrypoint(args):
    last = "recipe-entrypoint"
    try:
        new_recipe = True
        if not args or len(args.question) < 2:
            new_recipe = False
            last = "recipe-list"
            recipe = available_recipes()
            if not recipe:
                return
            recipe = get_recipe(recipe['prompt'], recipe['language'], recipe['id'])
            last = "recipe-select"
        else:
            prompt = " ".join(args.question[1:])

            print("Recipes currently utilize Terraform. Support for more methods coming soon.\n")
            # ui = selections.UI(LANG_OPTIONS, is_loading=False)
            # selection = ui.input()
            # print()
            selection = 0
            last = "recipe-init"
            recipe = init_recipe(prompt, LANG_OPTIONS[selection], loading=CancellableSimpleLoader("getting an outline ready..."))
            last = "recipe-edit-steps"
            recipe = edit_steps(recipe)

            last = "recipe-get"
            loading = CancellableSimpleLoader("generating files, please be patient as this can take several minutes...")
            recipe = get_recipe_execution(recipe, loading)

        last = "recipe-load-execution"
        executor = TerraformExecutor(recipe, regenerate_recipe_execution)
        result = executor.run()
        last = "recipe-execute"
        feedback({"event": "recipe-execute", "id": recipe.get('id'), "result": result})

        if new_recipe:
            print()
            print("Would you like to save this as a reusable recipe?")
            print()
            ui = selections.UI(["save", "exit"], is_loading=False)
            selection = ui.input()
            if selection == 0:
                last = "recipe-save"

                print("Would you like us to save the changes you made to the files?")
                ui = selections.UI(["save", "skip"], is_loading=False)
                selection = ui.input()

                if selection == 0:
                    recipe = executor.update()

                save_flow(recipe)
                print()
                print("To use a saved recipe, simply type 'um recipe'")
            print()
    except KeyboardInterrupt:
        feedback({"event": "recipe-cancel", "last_executed": last, "time": time.time()})
        pass
    except StreamException:
        print("Failed to stream the response back successfully, please try again")
        feedback({"event": "recipe-error", "error": "failed to stream"})
