import os.path
from dataclasses import dataclass
import logging

from promptops import settings
from promptops.similarity import VectorDB


@dataclass
class QATuple:
    question: str
    answer: str
    corrected: str

    @staticmethod
    def from_dict(data: dict) -> 'QATuple':
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


_db: VectorDB = None


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
