import logging
import os
import subprocess
from typing import Optional

import requests
import sys

from promptops import settings
from promptops import trace
from promptops import user
from promptops.ui import selections


def init_recipe(
    q: str,
):
    req = {
        "prompt": q,
        "trace_id": trace.trace_id,
        "platform": sys.platform,
        "shell": os.environ.get("SHELL"),
    }
    response = requests.post(
        settings.endpoint + "/recipe",
        json=req,
        headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
        },
    )
    if response.status_code != 200:
        # this exception completely destroys the ui
        raise Exception(f"there was problem with the response, status: {response.status_code}")

    data = response.json()

    if not data.get("steps"):
        raise Exception(f"missing steps")

    return data


def run(script: str, lang: str="shell") -> (int, Optional[str]):
    if lang == "shell":
        proc = subprocess.run(
            script, shell=True, start_new_session=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if proc.stdout and str(proc.stdout) != "":
            sys.stdout.write(proc.stdout.decode("utf-8"))
        if proc.stderr and str(proc.stderr) != "":
            sys.stdout.write(proc.stderr.decode("utf-8"))
        sys.stdout.flush()

        # history.add(scrub_secrets.scrub_line(".bash_history", cmd.script), proc.returncode)
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



def workflow_entrypoint(prompt):
    if not prompt.question or len(prompt.question) < 1:
        print("you must include a question")
        return

    # recipe = init_recipe(prompt)

    recipe = {
        "name": "Provide a name",
        "description": "Provide a description",
        "steps": [
            {
                "command": "aws iam create-role --role-name <lambda-role-name> --assume-role-policy-document file://<path-to-trust-policy-json-file>",
                "parameters": [
                    {
                        "name": "lambda-role-name",
                        "description": "name of the Lambda role",
                        "resolve": "aws iam list-roles --query 'Roles[].RoleName' --output text"
                    },
                    {
                        "name": "path-to-trust-policy-json-file",
                        "description": "local file path for trust policy document",
                        "create": "echo '{\n            \"Version\": \"2012-10-17\",\n            \"Statement\": [\n            {\n            \"Effect\": \"Allow\",\n            \"Principal\": {\n            \"Service\": \"lambda.amazonaws.com\"\n            },\n            \"Action\": \"sts:AssumeRole\"\n            }\n            ]\n            }' > trust-policy.json"
                    }
                ]
            },
            {
                "command": "aws iam attach-role-policy --role-name <lambda-role-name> --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                "parameters": [
                    {
                        "name": "lambda-role-name",
                        "description": "name of the Lambda execution role",
                        "resolve": "aws iam list-roles --query 'Roles[].RoleName' --output text"
                    },
                    {
                        "name": "policy-arn",
                        "description": "ARN of the AWSLambdaBasicExecutionRole policy",
                        "resolve": "aws iam list-policies --scope AWS --query 'Policies[?PolicyName==`AWSLambdaBasicExecutionRole`].Arn' --output text"
                    }
                ]
            },
            {
                "command": "aws lambda create-function --function-name <lambda-function-name> --runtime <runtime> --role <lambda-role-arn> --handler <handler> --zip-file fileb://<path-to-zip-file>",
                "parameters": [
                    {
                        "name": "<lambda-function-name>",
                        "description": "name of the Lambda function",
                        "resolve": "aws lambda list-functions --query 'Functions[].FunctionName' --output text"
                    },
                    {
                        "name": "<runtime>",
                        "description": "runtime environment for the Lambda function"
                    },
                    {
                        "name": "<lambda-role-arn>",
                        "description": "ARN of the IAM role that Lambda assumes when it executes the function",
                        "resolve": "aws iam list-roles --query 'Roles[?RoleName==`<lambda-role-name>`].Arn' --output text"
                    },
                    {
                        "name": "<handler>",
                        "description": "entry point of the Lambda function"
                    },
                    {
                        "name": "<path-to-zip-file>",
                        "description": "local file path for the ZIP file containing the Lambda function code",
                        "create": "zip -r <zip-file-name> <source-code-directory>"
                    }
                ]
            }
        ]
    }

    for step in recipe.get("steps"):
        execute_step(step)

    return
