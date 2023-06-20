import os
from dataclasses import dataclass
from typing import Tuple
from promptops.loading.cancellable import CancellableSimpleLoader
from promptops.recipes.executor import Executor
from promptops.recipes.run import run_command
from promptops.ui import selections
from promptops.ui.input import non_empty_input
from promptops.ui.prompts import confirm, GO_BACK


@dataclass
class Step:
    file: str
    content: str


class TerraformExecutor(Executor):
    def __init__(self, recipe, regen):
        self.recipe = recipe
        self.execution_steps = [Step(i.get('key'), i.get('value')) for i in recipe.get('execution')]
        self.parameters = recipe.get('parameters')
        directory = non_empty_input("enter a relative directory to store the terraform module in: ").strip()
        directory = directory if directory[0] != "/" else directory[1:]
        directory = directory if directory[-1] == "/" else directory + "/"
        self.directory = os.path.expanduser(directory)
        self.regen = regen

    def write_files(self):
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        print("working in directory: ", self.directory)
        self.resolve_unfilled_parameters()
        self.execute()
        print()
        print(f"please verify that the terraform files in directory {self.directory} are correct")
        print()


    def run(self):
        self.write_files()
        options = ["exit", "re-generate files", "terraform init"]

        while True:
            ui = selections.UI(options, is_loading=False)
            selection = ui.input()

            if selection == 0:
                break
            elif selection == 1:
                # todo: Create a cache of parameter values before regenerating!
                print()
                clarify = input("Provide more clarification (optional): ")
                self.recipe = self.regen(self.recipe, clarify, loading=CancellableSimpleLoader("regenerating terraform files..."))
                self.execution_steps = [Step(i.get('key'), i.get('value')) for i in self.recipe.get('execution')]
                self.parameters = self.recipe.get('parameters')
                self.clean()
                self.write_files()
            elif selection == 2:
                self.init()
                success, err = self.plan()
                if not success and confirm("would you like us to attempt to fix this error?") != GO_BACK:
                    self.fix(err)
                else:
                    if "terraform plan" not in options and "terraform apply" not in options:
                        options.extend(["terraform plan", "terraform apply"])
            elif selection == 3:
                success, err = self.plan()
                if not success and confirm("would you like us to attempt to fix this error?") != GO_BACK:
                    self.fix(err)
            elif selection == 4:
                success, err = self.apply()
                if success:
                    break
                else:
                    if confirm("would you like us to attempt to fix this error?") != GO_BACK:
                        self.fix(err)
            print()

    def resolve_unfilled_parameters(self):
        for parameter in self.parameters:
            value = None
            if parameter.get("options"):
                print(f"choose values for {parameter.get('parameter')}")
                options = parameter.get('options')
                while True:
                    ui = selections.UI(options, is_loading=False)
                    selection = ui.input()
                    if parameter.get('type') != "list":
                        value = options[selection]
                        break
                    else:
                        if not value:
                            options.append("done selecting")
                            value = [options[selection]]
                        else:
                            if options[selection] == "done selecting":
                                break
                            value.append(options[selection])
            else:
                value = input(parameter.get('description', f"enter a value for {parameter.get('parameter')}: ").strip() + " ")
                inp = None
                while parameter.get('type') == "list" and inp != "":
                    if type(value) is str:
                        value = [value]
                    inp = input(f"enter additional values for {parameter.get('parameter')} or hit enter to continue: ").strip()
                    value.append(inp)

            parameter['value'] = value

        return self.parameters

    @staticmethod
    def get_tf_value_from_param(parameter):
        if parameter['type'] == "list":
            items = [f'"{i}"' for i in parameter['value']]
            return f"[{' ,'.join(items)}]"
        else:
            return f"{parameter['value']}"


    def execute(self):
        for step in self.execution_steps:
            if not os.path.exists(self.directory + step.file):
                open(self.directory + step.file, 'w').close()
            for parameter in self.parameters:
                if parameter['parameter'] in step.content and parameter['value'].strip() != "":
                    var_name = f"<{parameter['parameter']}>"
                    step.content = step.content.replace(var_name, self.get_tf_value_from_param(parameter))

            with open(self.directory + step.file, "w") as outfile:
                outfile.write(step.content)

    def clean(self):
        for step in self.execution_steps:
            if os.path.exists(self.directory + step.file):
                os.remove(self.directory + step.file)

    def init(self) -> Tuple[bool, str]:
        if os.path.exists(self.directory + ".terraform/") or os.path.exists(self.directory + ".terraform.lock.hcl"):
            run_command("terraform plan", self.directory)
            return True, ""
        return run_command("terraform init", self.directory)

    def plan(self) -> Tuple[bool, str]:
        return run_command("terraform plan", self.directory)

    def apply(self) -> Tuple[bool, str]:
        return run_command("terraform apply", self.directory)\


    def fix(self, error):
        self.recipe = self.regen(self.recipe, "an error occurred", error, loading=CancellableSimpleLoader("attempting to fix terraform files..."))
        self.execution_steps = [Step(i.get('key'), i.get('value')) for i in self.recipe.get('execution')]
        self.parameters = self.recipe.get('parameters')
        self.clean()
        self.write_files()
        return


    def update(self) -> dict:
        param_used = {p['parameter']: False for p in self.parameters}
        for step in self.execution_steps:
            with open(self.directory + step.file, 'r') as f:
                edited_lines = "".join(f.readlines())

            for parameter in self.parameters:
                value = self.get_tf_value_from_param(parameter)
                if value in edited_lines:
                    param_used[parameter['parameter']] = True
                    edited_lines = edited_lines.replace(value, "<" + parameter['parameter'] + ">")

            print(f'before: \n {step.content} \n after: \n {edited_lines}\n')

            step.content = edited_lines


        self.recipe['execution'] = [{'key': step.file, 'value': step.content} for step in self.execution_steps]
        self.parameters = [p for p in self.parameters if param_used[p['parameter']]]

        return self.recipe
