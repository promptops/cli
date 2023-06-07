import os.path
import logging
from typing import Optional, List
import requests
import numpy as np

from promptops.similarity import VectorDB
from promptops.shells import get_shell
from promptops import settings
from promptops.user import user_id

_hist_db: Optional[VectorDB] = None


def get_history_db() -> VectorDB:
    """
    The history db records are dictionaries with the following keys:
        cmd: the command
        ignore: whether the command should be ignored
        error: whether the command is known to error
    :return:
    """
    global _hist_db
    if _hist_db is None:
        _hist_db = VectorDB()
        path = os.path.expanduser(settings.history_db_path)
        if os.path.exists(path):
            logging.debug("loading history db")
            _hist_db.load(path)
        logging.debug(f"loaded history db: {len(_hist_db)} records")
    return _hist_db


def check_history(embedding):
    history_db = get_history_db()
    results = history_db.search(embedding, k=3, min_similarity=0.8)
    results = [(obj, score) for obj, score in results if not isinstance(obj, dict) or not obj.get("ignore", False)]
    return results


def embedding_batch(cmds: List[str]) -> List[tuple[str, np.ndarray]]:
    resp = requests.post(
        settings.endpoint + "/embeddings",
        json={
            "batch": cmds,
        },
        headers={
            "user-agent": f"promptops-cli; user_id={user_id()}",
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


def index_history(show_progress: bool = None, max_history: int = 1000):
    progress = None
    if show_progress:
        from promptops.loading.progress import ProgressSpinner

        progress = ProgressSpinner(100)
        progress.increment(1)

    db = get_history_db()
    if max_history > 0:
        prev_commands = get_shell().get_recent_history(max_history + 1)
    else:
        prev_commands = get_shell().get_full_history()
    has_more = len(prev_commands) > max_history > 0
    if max_history > 0:
        prev_commands = prev_commands[-max_history:]

    if show_progress:
        progress.increment(3)

    indexed_commands = {obj if isinstance(obj, str) else obj["cmd"] for obj in db.objects}
    delta = list(set(prev_commands) - indexed_commands)
    batch_size = 32

    if show_progress is None and len(delta) > batch_size:
        from promptops.loading.progress import ProgressSpinner
        show_progress = True
        progress = ProgressSpinner(100)
        progress.increment(4)
    if show_progress:
        progress.increment(2)

    if len(delta) == 0:
        if show_progress:
            progress.set(100)
        return has_more

    start_progress = 6
    for i in range(0, len(delta), batch_size):
        for cmd, vector in embedding_batch(delta[i: i + batch_size]):
            db.add(vector, {"cmd": cmd, "ignore": False})
        if show_progress:
            progress.set(start_progress + (i + batch_size) / len(delta) * (100 - start_progress))

    db.save(os.path.expanduser(settings.history_db_path))

    if show_progress:
        progress.set(100)

    return has_more


def update_history():
    if settings.index_history:
        index_history()


def add(cmd: str, return_code: int):
    db = get_history_db()

    for obj in db.objects:
        if isinstance(obj, dict) and obj.get("cmd", None) == cmd:
            # we just need to update here
            obj["return_code"] = return_code
            db.save(os.path.expanduser(settings.history_db_path))
            return

    eb = embedding_batch([cmd])
    if len(eb) < 1:
        return
    cmd, vector = eb[0]
    db.add(vector, {"cmd": cmd, "ignore": False, "return_code": return_code})
    db.save(os.path.expanduser(settings.history_db_path))


if __name__ == "__main__":
    index_history(True)
