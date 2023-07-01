import os.path
import shutil

from promptops.similarity import embedding
from promptops import settings
from promptops.feedback import feedback

from .index_store import IndexStore
from .content import index_url, index_file


def is_url(source):
    return source.startswith("http://") or source.startswith("https://")


def mid_ellipsis(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    mid_len = (max_len - 3) // 2
    return s[:mid_len] + "..." + s[-(max_len - mid_len - 3):]


def entry_point(args):
    if args.action == "add":
        source_path = args.source
        print("indexing:", source_path)
        feedback({"event": "index_add", "path": source_path})
        if is_url(source_path):
            item_meta, db = index_url(source_path)
        else:
            item_meta, db = index_file(source_path)
        store = IndexStore(os.path.expanduser(settings.user_index_root))
        store.add_or_update(item_meta, db)
    elif args.action == "test":
        store = IndexStore(os.path.expanduser(settings.user_index_root))
        vector = embedding(args.query)
        items = store.search(vector, min_similarity=0.0)
        for item in items:
            print(item)
    elif args.action == "list":
        size = shutil.get_terminal_size()
        watch_width = len(" Watch ")
        last_indexed_width = max(len(" Last Indexed "), len(" 2020-01-01 00:00:00 "))
        location_width = size.columns - watch_width - last_indexed_width - 2
        store = IndexStore(os.path.expanduser(settings.user_index_root))
        print(f" Watch │{' Location'.ljust(location_width)}│ Last Indexed ")
        print(f"{'─' * watch_width}┼{'─' * location_width}┼{'─' * last_indexed_width}")
        for item in store.metadata:
            print(f"{('Y' if item.watch else '').center(watch_width)}│ {mid_ellipsis(item.item_location, location_width-1).ljust(location_width-1)}│ {item.last_indexed_on:%Y-%m-%d %H:%M:%S} ")
    elif args.action == "remove":
        source_path = args.source
        feedback({"event": "index_remove", "path": source_path})
        if is_url(source_path):
            item_type = "url"
        else:
            item_type = "file"
            source_path = os.path.abspath(source_path)
        store = IndexStore(os.path.expanduser(settings.user_index_root))
        for ix, item in enumerate(store.metadata):
            if item.item_location == source_path and item.item_type == item_type:
                break
        else:
            print(f"item not found: {source_path}")
            return
        store.remove(ix)
