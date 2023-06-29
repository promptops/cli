import json
import mimetypes
import datetime
import logging
import os
from typing import Union, Optional
import numpy as np
import requests

from promptops.trace import trace_id
from promptops import user
from promptops.loading.progress import ProgressSpinner
from promptops.secret import scrub_file
from promptops import settings
from promptops.similarity import VectorDB

from .index_store import ItemMetadata


def index_content(content: Union[str, bytes], content_type: str) -> VectorDB:
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
    prev_index = -1
    chunk_size = 1024
    spinner: Optional[ProgressSpinner] = None
    for chunk in response.iter_content(chunk_size=chunk_size):
        buffer += chunk
        while True:
            try:
                index = buffer.index(b"}", prev_index + 1)
            except ValueError:
                break
            try:
                decoded = json.loads(buffer[:index+1])
                buffer = buffer[index+1:]
                prev_index = -1

                if spinner is None:
                    spinner = ProgressSpinner(decoded["total"])
                spinner.set(decoded["done"])
                for fragment in decoded["fragments"]:
                    fragment: dict = fragment
                    embedding = fragment.pop("embedding")
                    db.add(np.array(embedding), fragment)
            except json.JSONDecodeError:
                prev_index = index
                continue
    if buffer:
        logging.info("failed to index the entire document")
        logging.debug("remaining buffer: " + repr(buffer))
    if spinner is not None:
        spinner.set(spinner.total)
    return db


def index_file(path: str) -> (ItemMetadata, VectorDB):
    mimetypes.add_type("text/markdown", ".md")
    mimetype, _ = mimetypes.guess_type(path)
    logging.debug("content-type: " + mimetype)
    with open(path, "r") as f:
        lines = f.readlines()
        lines = scrub_file(path, lines)
        db = index_content("".join(lines), mimetype)
    path = os.path.abspath(path)
    return ItemMetadata(
        item_type="file",
        item_location=path,
        index_location="",  # this is set by the store
        added_on=datetime.datetime.now(),
        last_indexed_on=datetime.datetime.now(),
        watch=True,
    ), db


def index_url(location: str) -> (ItemMetadata, VectorDB):
    response = requests.get(location)
    mimetype = response.headers["content-type"]
    logging.debug("content-type: " + mimetype)
    db = index_content(response.content, mimetype)
    return ItemMetadata(
        item_type="url",
        item_location=location,
        index_location="",  # this is set by the store
        added_on=datetime.datetime.now(),
        last_indexed_on=datetime.datetime.now(),
        watch=True,
    ), db
