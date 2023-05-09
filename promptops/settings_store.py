import json
import os

from promptops import settings


config_file_path = "~/.promptops/cli-config.json"


_loaded_data = None


def load():
    real_path = os.path.expanduser(config_file_path)
    if not os.path.exists(real_path):
        return
    with open(real_path) as f:
        data = json.load(f)
    global _loaded_data
    if _loaded_data is None:
        _loaded_data = data
    settings.endpoint = data.get("endpoint", settings.endpoint)
    settings.request_explanation = data.get("request_explanation", settings.request_explanation)
    settings.model = data.get("model", settings.model)
    settings.history_context = data.get("history_context", settings.history_context)
    settings.corrections_db_path = data.get("corrections_db_path", settings.corrections_db_path)
    settings.history_db_path = data.get("history_db_path", settings.history_db_path)


def _build_data():
    data = {
        "request_explanation": settings.request_explanation,
        "model": settings.model,
        "history_context": settings.history_context,
        "corrections_db_path": settings.corrections_db_path,
        "history_db_path": settings.history_db_path,
    }
    if settings.endpoint != settings.DEFAULT_ENDPOINT:
        data["endpoint"] = settings.endpoint
    return data


def save():
    real_path = os.path.expanduser(config_file_path)
    os.makedirs(os.path.dirname(real_path), exist_ok=True)
    data = _build_data()
    with open(real_path, "w") as f:
        json.dump(data, f, indent=2)


def is_changed() -> bool:
    data = _build_data()
    return data != _loaded_data
