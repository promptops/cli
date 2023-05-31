import datetime
import logging
import os.path
import json

import numpy as np
import requests
import mimetypes

from promptops.similarity import VectorDB, embedding
from promptops import settings
from promptops.trace import trace_id
from promptops import user
from promptops.loading.progress import ProgressSpinner
from promptops.secrets import scrub_file

from .index_store import IndexStore, ItemMetadata


def index_content(content: str, content_type: str) -> VectorDB:
    response = requests.post(
        settings.endpoint + "/index_data?trace_id=" + trace_id,
        headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
            "content-type": content_type,
            "content-length": str(len(content)),
        },
        data=content,
        stream=True,
    )

    db = VectorDB()
    buffer = b""
    chunk_size = 1024
    spinner: ProgressSpinner = None
    for chunk in response.iter_content(chunk_size=chunk_size):
        buffer += chunk
        try:
            decoded = json.loads(buffer)
            buffer = b""
        except json.JSONDecodeError:
            continue

        if spinner is None:
            spinner = ProgressSpinner(decoded["total"])
        spinner.set(decoded["done"])
        for fragment in decoded["fragments"]:
            fragment: dict = fragment
            embedding = fragment.pop("embedding")
            db.add(np.array(embedding), fragment)
    print("done!")
    if buffer:
        logging.warning("remaining buffer: " + repr(buffer))
    return db


def entry_point(args):
    if args.action == "add":
        source_path = args.source
        mimetypes.add_type("text/markdown", ".md")
        mimetype, _ = mimetypes.guess_type(source_path)
        print("indexing:", source_path)
        logging.debug("content-type: " + mimetype)
        with open(source_path, "r") as f:
            lines = f.readlines()
            lines = scrub_file(source_path, lines)
            db = index_content("".join(lines), mimetype)
        store = IndexStore(os.path.expanduser(settings.user_index_root))
        path = os.path.abspath(source_path)
        store.add_or_update(ItemMetadata(
            item_type="file",
            item_location=path,
            index_location="",
            added_on=datetime.datetime.now(),
            last_indexed_on=datetime.datetime.now(),
            watch=True,
        ), db)
    elif args.action == "test":
        store = IndexStore(os.path.expanduser(settings.user_index_root))
        vector = embedding(args.query)
        items = store.search(vector, min_similarity=0.0)
        for item in items:
            print(item)
    elif args.action == "list":
        store = IndexStore(os.path.expanduser(settings.user_index_root))
        print(f"Watch | Type  | {'Location':80} | Last Indexed")
        print(f"{'-' * 5} | {'-' * 5} | {'-' * 80} | {'-' * 19}")
        for item in store.metadata:
            print(f"{'  Y' if item.watch else ' ':5} | {item.item_type:5} | {item.item_location:80} | {item.last_indexed_on:%Y-%m-%d %H:%M:%S}")
    elif args.action == "remove":
        source_path = os.path.abspath(args.source)
        store = IndexStore(os.path.expanduser(settings.user_index_root))
        for ix, item in enumerate(store.metadata):
            if item.item_location == source_path:
                break
        else:
            print(f"item not found: {source_path}")
            return
        store.remove(ix)
