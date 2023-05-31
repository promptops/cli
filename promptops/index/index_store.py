import logging
import random
from dataclasses import dataclass
from datetime import datetime
import os
import json
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from promptops.similarity import VectorDB
import typing


@dataclass
class ItemMetadata:
    item_type: str
    item_location: str
    index_location: str
    added_on: datetime
    last_indexed_on: datetime
    watch: bool

    def to_dict(self):
        data = dict(self.__dict__)
        data["added_on"] = self.added_on.isoformat()
        data["last_indexed_on"] = self.last_indexed_on.isoformat()
        return data

    @staticmethod
    def from_dict(data: dict) -> 'ItemMetadata':
        data = dict(data)
        data["added_on"] = datetime.fromisoformat(data["added_on"])
        data["last_indexed_on"] = datetime.fromisoformat(data["last_indexed_on"])
        return ItemMetadata(**data)


@dataclass
class ItemFragment:
    fragment: str
    location: dict = None


@dataclass
class SearchResult:
    item: ItemMetadata
    fragment: ItemFragment
    score: float


class IndexStore:
    def __init__(self, root: str):
        self._root = root
        self.metadata: list[ItemMetadata] = []
        self._meta_path = os.path.join(root, "meta.json")
        self._embeddings_dir = os.path.join(root, "embeddings")
        self.load_meta()

    def load_meta(self):
        path = self._meta_path
        if not os.path.exists(path):
            return
        with open(path, "r") as f:
            data = json.load(f)
        self.metadata = [ItemMetadata.from_dict(item) for item in (data.get("metadata", []) or [])]

    def save_meta(self):
        path = self._meta_path
        dir_name = os.path.dirname(path)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
        # make sure we don't corrupt the file
        tmp_path = path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump({
                "metadata": [item.to_dict() for item in self.metadata]
            }, f, indent=4)
        os.rename(tmp_path, path)

    def add_or_update(self, item: ItemMetadata, db: VectorDB):
        dir_name = self._embeddings_dir
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

        for existing in self.metadata:
            if item.item_location == existing.item_location and item.item_type == existing.item_type:
                item.index_location = existing.index_location
                existing.last_indexed_on = item.last_indexed_on
                break
        else:
            while True:
                index = "".join(random.choices("0123456789abcdefghijklmnopqrstuvwxyz", k=16)) + ".npz"
                if not os.path.exists(os.path.join(dir_name, index)):
                    break
            item.index_location = index
            self.metadata.append(item)
        db.save(os.path.join(dir_name, item.index_location))
        self.save_meta()

    def remove(self, index: int):
        item = self.metadata[index]
        os.remove(os.path.join(self._embeddings_dir, item.index_location))
        del self.metadata[index]
        self.save_meta()

    def search(self, vector: np.array, k=3, min_similarity=0.8, accept_source: typing.Callable[[ItemMetadata], bool] = None, context: int=1) -> list[SearchResult]:
        futures = []
        items = []

        def search_item(item_meta: ItemMetadata):
            db = VectorDB()
            db.load(os.path.join(self._embeddings_dir, item_meta.index_location))
            results = db.argsearch(vector, k=k, min_similarity=min_similarity)
            return [SearchResult(item_meta, ItemFragment("".join(item["text"] for item in db.objects[ix-context: ix+context+1])), score)
                    for ix, score in results]

        with ThreadPoolExecutor(max_workers=16) as executor:
            for item in self.metadata:
                if accept_source and not accept_source(item):
                    continue

                futures.append(executor.submit(search_item, item))
                items.append(item)

        results = []
        for item, future in zip(items, futures):
            try:
                results.extend(future.result())
            except Exception as e:
                logging.debug(f"error while searching {item}", exc_info=e)

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:k]
