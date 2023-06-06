import os
import subprocess
from dataclasses import dataclass

from promptops.loading import loading_animation, Simple
from promptops.ui import selections
from promptops.ui.input import non_empty_input


@dataclass
class Step:
    file: str
    content: str


class TerraformExecutor:
    def __init__(self, recipe):
        self.recipe = recipe
        self.execution_steps = [Step(i.get('file'), i.get('content')) for i in recipe.get('execution')]
        self.parameters = recipe.get('parameters')

        directory = non_empty_input("enter a relative directory to store the terraform module in: ").strip()
        directory = directory if directory[0] != "/" else directory[1:]
        directory = directory if directory[-1] == "/" else directory + "/"
        self.directory = os.path.expanduser(directory)

    def write_files(self):
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        print("working in directory: ", self.directory)
        self.resolve_unfilled_parameters()
        self.execute()
        print()
        print(f"please verify that the terraform files in directory {self.directory} are correct")
        print()


    def run(self, regen):
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
                with loading_animation(Simple("regenerating terraform files...")):
                    self.recipe = regen(self.recipe, clarify)
                self.execution_steps = [Step(i.get('file'), i.get('content')) for i in self.recipe.get('execution')]
                self.parameters = self.recipe.get('parameters')
                self.clean()
                self.write_files()
            elif selection == 2:
                self.init()
                options.extend(["terraform plan", "terraform apply"])
            elif selection == 3:
                if not self.plan():
                    self.fix()
            elif selection == 4:
                if self.apply():
                    break
                else:
                    self.fix()
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
                value = input(parameter.get('description').strip() + " ")
                inp = None
                while parameter.get('type') == "list" and inp != "":
                    if type(value) is str:
                        value = [value]
                    inp = input(f"enter additional values for {parameter.get('parameter')} or nothing to continue: ").strip()
                    value.append(inp)

            parameter['value'] = value

        return self.parameters

    def execute(self):
        for step in self.execution_steps:
            if not os.path.exists(self.directory + step.file):
                open(self.directory + step.file, 'w').close()
            for parameter in self.parameters:
                if parameter['parameter'] in step.content:
                    if parameter['type'] == "list":
                        items = [f'"{i}"' for i in parameter['value']]
                        value = f"[{' ,'.join(items)}]"
                    else:
                        value = f"{parameter['value']}"

                    var_name = f"<{parameter['parameter']}>"
                    step.content = step.content.replace(var_name, value)

            with open(self.directory + step.file, "w") as outfile:
                outfile.write(step.content)

    def clean(self):
        for step in self.execution_steps:
            if os.path.exists(self.directory + step.file):
                os.remove(self.directory + step.file)

    def init(self):
        subprocess.run(f"ls {self.directory}", shell=True, start_new_session=True,)
        subprocess.run("terraform init", shell=True, start_new_session=True, cwd=self.directory)

    def plan(self) -> bool:
        return subprocess.run("terraform plan", shell=True, start_new_session=True, cwd=self.directory).returncode == 0

    def apply(self) -> bool:
        return subprocess.run("terraform apply", shell=True, start_new_session=True, cwd=self.directory).returncode == 0

    def fix(self):
        print("Auto-fix coming soon.")
        return

