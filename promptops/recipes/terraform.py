import os
import subprocess
from dataclasses import dataclass

from promptops.ui import selections


@dataclass
class Step:
    file: str
    content: str


class TerraformExecutor:
    def __init__(self, obj, directory):
        print(obj)
        self.steps = [Step(i.get('file'), i.get('content')) for i in obj.get('steps')]
        self.parameters = obj.get('parameters')
        self.directory = os.path.expanduser(directory)

    def run(self):
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        print("working in director: ", self.directory)
        self.resolve_unfilled_parameters()
        self.execute()

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
                    step.content = step.content.replace(parameter['parameter'], parameter['value'])

            with open(self.directory + step.file, "w") as outfile:
                outfile.write(step.content)

    def init(self):
        subprocess.run(f"ls {self.directory}", shell=True, start_new_session=True,)
        subprocess.run("terraform init", shell=True, start_new_session=True, cwd=self.directory)

    def plan(self):
        subprocess.run("terraform plan", shell=True, start_new_session=True, cwd=self.directory)

    def apply(self):
        subprocess.run("terraform apply", shell=True, start_new_session=True, cwd=self.directory)

    def fix(self):
        print("attempting to fix terraform files in " + self.directory)


if __name__ == "__main__":
    obj = {'type': 'terraform', 'steps': [{
                                        'content': 'variable "aws_region" {\n  type    = string\n  default = "us-west-2"\n}\n\nprovider "aws" {\n  region = var.aws_region\n}\n',
                                        'file': 'provider.tf'}, {
                                        'content': 'resource "aws_iam_role" "lambda_role" {\n  name = "my_lambda_role"\n\n  assume_role_policy = jsonencode({\n    Version = "2012-10-17"\n    Statement = [\n      {\n        Action = "sts:AssumeRole"\n        Effect = "Allow"\n        Principal = {\n          Service = "lambda.amazonaws.com"\n        }\n      }\n    ]\n  })\n}\n',
                                        'file': 'iam_role.tf'}, {
                                        'content': 'resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {\n  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"\n  role       = aws_iam_role.lambda_role.name\n}\n',
                                        'file': 'iam_role_policy.tf'}, {
                                        'content': 'variable "function_name" {\n  type = string\n}\n\nvariable "runtime" {\n  type = string\n}\n\nvariable "handler" {\n  type = string\n}\n\nvariable "filename" {\n  type = string\n}\n',
                                        'file': 'variables.tf'}, {
                                        'content': 'resource "aws_lambda_function" "example" {\n  function_name = var.function_name\n  filename      = var.filename\n  runtime       = var.runtime\n  handler       = var.handler\n  role          = aws_iam_role.lambda_role.arn\n\n  source_code_hash = filebase64sha256(var.filename)\n\n  environment {\n    variables = {\n      EXAMPLE_VAR = "example_value"\n    }\n  }\n}\n',
                                        'file': 'lambda_function.tf'}, {
                                        'content': 'resource "aws_apigatewayv2_api" "api_gateway" {\n  name          = "example_api_gateway"\n  protocol_type = "HTTP"\n}\n\nresource "aws_apigatewayv2_integration" "lambda_integration" {\n  api_id              = aws_apigatewayv2_api.api_gateway.id\n  integration_type    = "AWS_PROXY"\n  integration_uri     = aws_lambda_function.example.invoke_arn\n  payload_format_version = "2.0"\n\n  connection_type = "INTERNET"\n}\n\nresource "aws_apigatewayv2_route" "example_route" {\n  api_id    = aws_apigatewayv2_api.api_gateway.id\n  route_key = "ANY /{proxy+}"\n  target     = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"\n}\n\nresource "aws_apigatewayv2_stage" "example_stage" {\n  api_id     = aws_apigatewayv2_api.api_gateway.id\n  name       = "test"\n  auto_deploy = true\n}\n\nresource "aws_lambda_permission" "invoke_lambda" {\n  function_name = aws_lambda_function.example.function_name\n  action        = "lambda:InvokeFunction"\n  principal     = "apigateway.amazonaws.com"\n  source_arn    = "${aws_apigatewayv2_route.example_route.execution_arn}/*/*"\n}\n',
                                        'file': 'api_gateway.tf'}],
     'parameters': [{'parameter': 'function_name', 'description': 'Name of the AWS Lambda function', 'type': 'string'},
                    {'parameter': 'runtime', 'description': 'Runtime environment for the Lambda function',
                     'type': 'string'},
                    {'parameter': 'handler', 'description': 'Handler function in Lambda', 'type': 'string'},
                    {'parameter': 'filename', 'description': 'Path to the zip file containing the function code',
                     'type': 'string'}]}

    exe = TerraformExecutor(obj=obj, directory="tf-gen-test/")
    exe.run()
    exe.init()
