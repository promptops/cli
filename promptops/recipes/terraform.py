import os
import subprocess
from dataclasses import dataclass

from promptops.ui import selections


@dataclass
class Step:
    file: str
    content: str


_DEBUG = False


class TerraformExecutor:
    def __init__(self, obj, directory):
        if _DEBUG:
            print(obj)
        self.steps = [Step(i.get('file'), i.get('content')) for i in obj.get('steps')]
        self.parameters = obj.get('parameters')
        directory = directory.strip()
        directory = directory if directory[0] != "/" else directory[1:]
        directory = directory if directory[-1] == "/" else directory + "/"
        self.directory = os.path.expanduser(directory)

    def run(self):
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        print("working in directory: ", self.directory)
        self.resolve_unfilled_parameters()
        self.execute()

        print()
        print(f"please verify that the terraform files in directory {self.directory} are correct")
        print()

        options = ["exit", "re-generate files", "terraform init"]

        while True:
            ui = selections.UI(options, is_loading=False)
            selection = ui.input()

            if selection == 0:
                break
            elif selection == 1:
                self.fix()
                print("Coming soon. Please try a different option.")
            elif selection == 2:
                self.init()
                options.extend(["terraform plan", "terraform apply"])
            elif selection == 3:
                self.plan()
            elif selection == 4:
                if self.apply():
                    break
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
                value = input(f"enter value for {parameter.get('parameter')}: ").strip()
                inp = None
                while parameter.get('type') == "list" and inp != "":
                    if type(value) is str:
                        value = [value]
                    inp = input(f"enter value for {parameter.get('parameter')} or nothing to continue: ").strip()
                    value.append(inp)

            parameter['value'] = value

        return self.parameters

    def execute(self):
        for step in self.steps:
            if not os.path.exists(self.directory + step.file):
                open(self.directory + step.file, 'w').close()
            for parameter in self.parameters:
                if parameter['parameter'] in step.content:
                    var_name = f"<{parameter['parameter']}>"
                    value = f"\"{parameter['value']}\""
                    step.content = step.content.replace(var_name, value)

            with open(self.directory + step.file, "w") as outfile:
                outfile.write(step.content)

    def init(self):
        subprocess.run(f"ls {self.directory}", shell=True, start_new_session=True,)
        subprocess.run("terraform init", shell=True, start_new_session=True, cwd=self.directory)

    def plan(self) -> bool:
        return subprocess.run("terraform plan", shell=True, start_new_session=True, cwd=self.directory).returncode == 0

    def apply(self) -> bool:
        return subprocess.run("terraform apply", shell=True, start_new_session=True, cwd=self.directory).returncode == 0

    def fix(self):
        # print("attempting to fix terraform files in " + self.directory)
        return


if __name__ == "__main__":
    obj = {'type': 'terraform', 'steps': [{'content': 'resource "aws_iam_role" "lambda_exec" {\n  name = "lambda-exec"\n\n  assume_role_policy = jsonencode({\n    Version = "2012-10-17"\n    Statement = [\n      {\n        Action = "sts:AssumeRole"\n        Effect = "Allow"\n        Principal = {\n          Service = "lambda.amazonaws.com"\n        }\n      }\n    ]\n  })\n}', 'file': 'iam.tf'}, {'content': 'resource "aws_iam_role_policy_attachment" "attach_policy" {\n  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"\n  role       = aws_iam_role.lambda_exec.name\n}', 'file': 'iam.tf'}, {'content': 'resource "aws_lambda_function" "main" {\n  function_name    = "example_lambda"\n  filename         = <zip_file_path>\n  source_code_hash = filebase64sha256(<zip_file_path>).\n  role             = aws_iam_role.lambda_exec.arn\n  handler          = <handler>\n  runtime          = <runtime>\n}', 'file': 'lambda.tf'}, {'content': 'resource "aws_apigatewayv2_api" "main" {\n  name          = "lambda-api-gateway"\n  protocol_type = "HTTP"\n}', 'file': 'api-gateway.tf'}, {'content': 'resource "aws_apigatewayv2_integration" "main" {\n  api_id           = aws_apigatewayv2_api.main.id\n  integration_type = "AWS_PROXY"\n  integration_uri  = aws_lambda_function.main.invoke_arn\n  payload_format_version = "2.0"\n}\n\nresource "aws_apigatewayv2_route" "main" {\n  api_id    = aws_apigatewayv2_api.main.id\n  route_key = "ANY /{proxy+}"\n  target    = "integrations/${aws_apigatewayv2_integration.main.id}"\n}', 'file': 'api-gateway.tf'}, {'content': 'resource "aws_apigatewayv2_stage" "main" {\n  api_id     = aws_apigatewayv2_api.main.id\n  name       = "$default"\n  auto_deploy = true\n}', 'file': 'api-gateway.tf'}, {'content': 'resource "aws_lambda_permission" "main" {\n  action        = "lambda:InvokeFunction"\n  function_name = aws_lambda_function.main.function_name\n  principal     = "apigateway.amazonaws.com"\n  source_arn    = aws_apigatewayv2_api.main.execution_arn\n}', 'file': 'lambda.tf'}], 'parameters': [{'parameter': 'zip_file_path', 'description': 'Path to the zipped Lambda function code', 'type': 'string'}, {'parameter': 'handler', 'description': 'Lambda function handler (e.g., index.handler)', 'type': 'string'}, {'parameter': 'runtime', 'description': 'Runtime for the Lambda function (e.g., nodejs14.x)', 'options': ['nodejs14.x', 'python3.8', 'go1.x'], 'type': 'string'}]}

    exe = TerraformExecutor(obj=obj, directory="tf-gen-test/")
    exe.run()
