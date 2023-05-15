import os.path
import logging
from typing import Optional, List
import requests
import numpy as np
import subprocess

from promptops.similarity import VectorDB
from promptops.shells import get_shell
from promptops import settings, settings_store
from promptops.user import user_id

_hist_db: Optional[VectorDB] = None


dry_run_option = {
    "aws": "--dry-run"
}


def validate(cmd) -> bool:
    chunks = cmd.split(" ")
    if len(chunks) == 0:
        return False

    name = chunks[0]
    if dry_run_option.get(name):
        proc = subprocess.run(cmd + " " + dry_run_option.get(name))
        return proc.returncode == 0

    return True


def get_history_db(history_db_path: str) -> VectorDB:
    """
    The history db records are dictionaries with the following keys:
        cmd: the command
        ignore: whether the command should be ignored
    :param history_db_path:
    :return:
    """
    global _hist_db
    if _hist_db is None:
        _hist_db = VectorDB()
        path = os.path.expanduser(history_db_path)
        if os.path.exists(path):
            logging.debug("loading history db")
            _hist_db.load(path)
        logging.debug(f"loaded history db: {len(_hist_db)} records")
    return _hist_db


def check_history(embedding):
    history_db = get_history_db(settings.history_db_path)
    results = history_db.search(embedding)
    return results


def embedding_batch(endpoint: str, cmds: List[str]) -> List[tuple[str, np.ndarray]]:
    resp = requests.post(
        endpoint + "/embeddings",
        json={
            "batch": cmds,
        },
        headers={
            "user-agent": f"promptops-cli; user_id={user_id}",
        },
    )

    try:
        resp.raise_for_status()
    except Exception as e:
        logging.debug(f"error getting embeddings: {e}, {resp.text}")
        raise
    # best effort for now
    result = resp.json().get("result", [])
    items = []
    for item in result:
        cmd = item["text"]
        vector = np.array(item["embeddings"])
        items.append((cmd, vector))

    return items


def index_history(show_progress=False):
    progress = None
    if show_progress:
        from promptops.loading.progress import ProgressSpinner
        progress = ProgressSpinner(100)
        progress.increment(1)

    db = get_history_db(settings.history_db_path)
    prev_commands = get_shell().get_full_history()

    if show_progress:
        progress.increment(3)

    indexed_commands = {obj if isinstance(obj, str) else obj["cmd"] for obj in db.objects}
    delta = list(set(prev_commands) - indexed_commands)

    if show_progress:
        progress.increment(7)

    if len(delta) == 0:
        if show_progress:
            progress.set(100)
        return

    batch_size = 32
    progress_inc = (100 - 10) // (len(delta) / batch_size)

    for i in range(0, len(delta), batch_size):
        for cmd, vector in embedding_batch(settings.endpoint, delta[i: i + batch_size]):
            db.add(vector, {"cmd": cmd, "ignore": False})
        if show_progress:
            progress.increment(progress_inc)

    db.save(os.path.expanduser(settings.history_db_path))

    if show_progress:
        progress.set(100)


if __name__ == "__main__":
    index_history(True)
