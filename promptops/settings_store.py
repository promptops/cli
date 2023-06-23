import json
import logging
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
    settings.index_history = data.get("index_history", settings.index_history)
    settings.gen_commit_message = data.get("gen_commit_message", settings.gen_commit_message)


def _build_data():
    data = {
        "request_explanation": settings.request_explanation,
        "model": settings.model,
        "history_context": settings.history_context,
        "corrections_db_path": settings.corrections_db_path,
        "history_db_path": settings.history_db_path,
        "index_history": settings.index_history,
        "gen_commit_message": settings.gen_commit_message,
    }
    if settings.endpoint != settings.DEFAULT_ENDPOINT:
        data["endpoint"] = settings.endpoint
    return data


def save():
    real_path = os.path.expanduser(config_file_path)
    os.makedirs(os.path.dirname(real_path), exist_ok=True)
    data = _build_data()
    global _loaded_data
    _loaded_data = data
    with open(real_path, "w") as f:
        json.dump(data, f, indent=2)


def set_history_context(history_context: int):
    settings.history_context = history_context
    save()


def set_index_history(index: bool):
    settings.index_history = index
    save()


def dict_diff_keys(dict1, dict2):
    keys1 = set(dict1.keys())
    keys2 = set(dict2.keys())

    diff_keys = keys1 ^ keys2
    common_keys = keys1 & keys2
    return diff_keys | {key for key in common_keys if dict1[key] != dict2[key]}


def is_changed() -> bool:
    data = _build_data()
    diff_keys = dict_diff_keys(data, _loaded_data or {})
    diff_keys.discard("endpoint")
    logging.debug(f"diff_keys: {diff_keys}")
    logging.debug("data: %s", data)
    logging.debug("_loaded_data: %s", _loaded_data)
    return len(diff_keys) > 0
