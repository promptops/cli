import os.path

from promptops.similarity import embedding
from promptops import settings
from promptops.feedback import feedback

from .index_store import IndexStore
from .content import index_url, index_file


def is_url(source):
    return source.startswith("http://") or source.startswith("https://")


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
        store = IndexStore(os.path.expanduser(settings.user_index_root))
        print(f" Watch │ Type │ {'Location':80} │ Last Indexed")
        print(f" {'─' * 6}┼{'─' * 6}┼{'─' * 82}┼{'─' * 19}")
        for item in store.metadata:
            print(f" {'  Y' if item.watch else ' ':5} │ {item.item_type:4} │ {item.item_location:80} │ {item.last_indexed_on:%Y-%m-%d %H:%M:%S}")
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
