import logging
import os.path
import numpy as np
import requests

from promptops import settings
from promptops import user
from functools import lru_cache
from promptops import trace


class VectorDB(object):
    def __init__(self):
        self.vectors = np.zeros((0, 0))
        self.objects = []

    def add(self, vector, obj):
        if len(self.vectors) == 0:
            self.vectors = np.expand_dims(vector, axis=0)
        else:
            self.vectors = np.vstack((self.vectors, vector))
        self.objects.append(obj)

    def update_or_add(self, vector, obj, equals: callable=None):
        if equals is None:
            equals = lambda a, b: a == b
        for i, o in enumerate(self.objects):
            if equals(o, obj):
                self.vectors[i] = vector
                return
        self.add(vector, obj)

    def search(self, vector, k=1, min_similarity=0.8):
        # compute cosine similarity
        if len(self.vectors) == 0:
            return []
        scores = np.dot(vector, self.vectors.T).flatten()
        # rank results
        results = np.argsort(scores)[::-1]
        return [(self.objects[i], scores[i]) for i in results[:k] if scores[i] > min_similarity]

    def argsearch(self, vector, k=1, min_similarity=0.8):
        # compute cosine similarity
        if len(self.vectors) == 0:
            return []
        scores = np.dot(vector, self.vectors.T).flatten()
        # rank results
        results = np.argsort(scores)[::-1]
        return [(i, scores[i]) for i in results[:k] if scores[i] > min_similarity]

    def index(self, obj):
        return self.objects.index(obj)

    def remove(self, index):
        self.vectors = np.delete(self.vectors, index, axis=0)
        del self.objects[index]

    def save(self, path):
        dir_name = os.path.dirname(path)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
        # make sure we don't corrupt the file
        tmp_path = path + ".tmp"
        with open(tmp_path, "wb") as f:
            np.savez(f, vectors=self.vectors, objects=self.objects)
        os.rename(tmp_path, path)

    def load(self, path):
        data = np.load(path, allow_pickle=True)
        self.vectors = data["vectors"]
        self.objects = data["objects"].tolist()

    def __len__(self):
        return len(self.objects)

    def __getitem__(self, index):
        return self.objects[index]

    def __iter__(self):
        return iter(self.objects)

    def __contains__(self, item):
        return item in self.objects

    def __repr__(self):
        return f"<VectorDB {len(self)} objects>"

    def __str__(self):
        return repr(self)


@lru_cache(maxsize=1_000)
def embedding(text: str) -> np.ndarray:
    resp = requests.post(
        settings.endpoint + "/embeddings",
        json={
            "text": text,
            "trace_id": trace.trace_id,
        },
        headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
        },
    )
    resp.raise_for_status()

    data = resp.json()
    try:
        vector = data["embeddings"]
        return np.array(vector)
    except KeyError:
        logging.debug("response: %s", data)
        raise
