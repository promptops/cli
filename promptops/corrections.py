import os.path
from dataclasses import dataclass
import logging
from typing import Optional

import requests
from promptops import settings
from promptops.similarity import VectorDB
from promptops.trace import trace_id
from promptops.user import user_id
from promptops import scrub_secrets


@dataclass
class QATuple:
    question: str
    answer: str
    corrected: str

    @staticmethod
    def from_dict(data: dict) -> "QATuple":
        return QATuple(
            question=data["question"],
            answer=data["answer"],
            corrected=data["corrected"],
        )

    def to_dict(self):
        return {
            "question": self.question,
            "answer": self.answer,
            "corrected": self.corrected,
        }


_db: Optional[VectorDB] = None


def get_db() -> VectorDB:
    global _db
    if _db is None:
        _db = VectorDB()
        path = os.path.expanduser(settings.corrections_db_path)
        if os.path.exists(path):
            logging.debug("loading corrections db")
            _db.load(path)
        logging.debug(f"loaded corrections db: {len(_db)} records")

    return _db


def get_correction(prompt: str, command: str, error: str) -> Optional[str]:
    resp = requests.post(
        settings.endpoint + "/correction",
        json={
            "prompt": prompt,
            "command": scrub_secrets.scrub_line(".bash_history", command),
            "error": error,
            "model": settings.model,
            "trace_id": trace_id,
        },
        headers={
            "user-agent": f"promptops-cli; user_id={user_id()}",
        },
    )

    try:
        resp.raise_for_status()
    except Exception as e:
        logging.debug(f"error getting correction: {e}, {resp.text}")
        raise
    # best effort for now
    result = resp.json().get("command", None)

    return result
