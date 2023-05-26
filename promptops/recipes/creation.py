import logging
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


def init_recipe(
    q: str,
    steps: dict,
    language: str
):
    req = {
        "prompt": q,
        "trace_id": trace.trace_id,
        "platform": sys.platform,
        "steps": steps.get('steps'),
        "questions": steps.get('questions'),
        "parameters": steps.get('parameters')
    }
    if language == LANG_SHELL:
        req['shell'] = os.environ.get('SHELL')
    else:
        req['language'] = language

    response = requests.post(
        settings.endpoint + "/recipe",
        json=req,
        headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
        },
    )
    if response.status_code != 200:
        raise Exception(f"there was problem with the response, status: {response.status_code}")

    data = response.json()

    if not data.get("steps"):
        raise Exception(f"missing steps")

    return data


def get_steps(prompt: str, language: str):
    req = {
        "prompt": prompt,
        "trace_id": trace.trace_id,
        "platform": sys.platform,
        "language": language,
    }

    if language == LANG_SHELL:
        req['shell'] = os.environ.get("SHELL")

    response = requests.post(
        settings.endpoint + "/recipe/steps",
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


def execute_step(step):
    print(f"executing step \n command: {step.get('command')}")
    print()

    for parameter in step.get("parameters"):
        print(f"parameter: {parameter.get('name')}")
        options = ["describe"]

        if parameter.get("resolve"):
            options.append("resolve")
        if parameter.get("create"):
            options.append("create")
        if parameter.get("options"):
            options.append("select")
        options.append("replace")
        ui = selections.UI(options, is_loading=False)
        selection = ui.input()

        option = options[selection]

        if option == "resolve" or option == "create":
            result = run(parameter.get(option))
        if option == "options":
            select_ui = selections.UI(parameter.get("options"), is_loading=False)
            selected_option = select_ui.input()
            print(selected_option)
        if options == "replace":
            value = input("enter a value for the parameter: ")


def print_steps(steps):
    for i, step in enumerate(steps):
        print(f"{i + 1}. {step}")
    print()


def edit_steps(steps_obj):
    steps = steps_obj.get('steps', [])
    print("Based on your requirements, I've set the project outline to include the following steps ")

    print_steps(steps)

    options = ["edit in vim", "clarify", "continue"]
    selection = None
    while selection != 2:
        ui = selections.UI(options, is_loading=False)
        selection = ui.input()
        if selection == 0:
            edited = edit_with_vim("\n".join(steps))
            steps_obj['steps'] = edited.split("\n")
            steps = steps_obj['steps']
            print_steps(steps)
        elif selection == 1:
            # clarification = input("enter more details: ")
            print("Sorry! Automated clarification coming soon!")

    parameters = steps_obj.get('parameters', [])

    steps_obj['parameters'] = {}
    for parameter in parameters:
        question = parameter.get('question')
        param = parameter.get('parameter')
        if parameter.get("options"):
            print(question)
            ui = selections.UI(parameter.get('options'), is_loading=False)
            selection = ui.input()
            value = parameter.get('options')[selection]
        else:
            value = input(f"{question}: ")
        steps_obj['parameters'][param] = value

    questions = steps_obj.get('clarification_questions', [])
    steps_obj['questions'] = {}
    for question in questions:
        steps_obj['questions'][question] = input(f"{question}: ")

    return steps_obj


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
        steps = get_steps(prompt, LANG_OPTIONS[selection])
    steps = edit_steps(steps)

    with loading_animation(Simple("processing instructions...")):
        recipe = init_recipe(prompt, steps, LANG_OPTIONS[selection])

    executor = TerraformExecutor(recipe, input("enter a relative directory to store the terraform in: "))
    executor.run()
    return
