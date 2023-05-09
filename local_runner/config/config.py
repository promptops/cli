import os
from dataclasses import dataclass


@dataclass
class Config:
    ws_url: str
    auth_url: str
    credentials_file: str
    python_path: str
    shell_path: str
    registration_url: str
    registration_timeout: int
    registration_code_rotation: int
    parallelism: int


ENV_PREFIX = "PROMPTOPS"

ENV_WS_URL = f"{ENV_PREFIX}_WS_URL"
ENV_AUTH_URL = f"{ENV_PREFIX}_AUTH_URL"
ENV_CREDENTIALS_FILE = f"{ENV_PREFIX}_CREDENTIALS_FILE"
ENV_PYTHON_PATH = f"{ENV_PREFIX}_PYTHON_PATH"
ENV_SHELL_PATH = f"{ENV_PREFIX}_SHELL_PATH"
ENV_REGISTRATION_URL = f"{ENV_PREFIX}_REGISTRATION_URL"


def default() -> Config:
    cfg = Config(
        ws_url="wss://local-runner-api.global.ctrlstack.com",
        auth_url="https://authorization-tokens.global.ctrlstack.com/token",
        credentials_file="~/.promptops/credentials.json",
        python_path="python",
        shell_path=os.getenv("SHELL"),
        registration_url="wss://local-runner-registrar.global.ctrlstack.com",
        registration_timeout=30 * 60,  # 30 minutes in seconds
        registration_code_rotation=5 * 60,  # 5 minutes in seconds
        parallelism=2,  # the number of concurrent tasks to run
    )

    if (url := os.getenv(ENV_WS_URL)) is not None:
        cfg.ws_url = url
    if (url := os.getenv(ENV_AUTH_URL)) is not None:
        cfg.auth_url = url
    if (file := os.getenv(ENV_CREDENTIALS_FILE)) is not None:
        cfg.credentials_file = file
    if (path := os.getenv(ENV_PYTHON_PATH)) is not None:
        cfg.python_path = path
    if (path := os.getenv(ENV_SHELL_PATH)) is not None:
        cfg.shell_path = path
    if (url := os.getenv(ENV_REGISTRATION_URL)) is not None:
        cfg.registration_url = url

    return cfg
