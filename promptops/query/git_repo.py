import typing
import colorama
import os
from promptops.ui import selections
from promptops import gitaware
from promptops.loading.context import loading_animation
from promptops.loading.simple import Simple
from promptops.index import index_store, content
from promptops import settings
from promptops import feedback


def _is_processed(git_root):
    fname = os.path.expanduser(os.path.join(settings.user_index_root, "git_roots.txt"))
    if not os.path.exists(fname):
        return False
    with open(fname, "r") as f:
        for line in f.readlines():
            if line.strip() == git_root:
                return True


def _set_processed(git_root):
    fname = os.path.expanduser(os.path.join(settings.user_index_root, "git_roots.txt"))
    if not os.path.exists(fname):
        os.makedirs(os.path.dirname(fname), exist_ok=True)
        with open(fname, "w") as f:
            pass
    with open(fname, "a") as f:
        f.write(git_root + "\n")


def _discover_indexable_files(root, accept_file: typing.Callable[[str, str], bool] = None) -> list[str]:
    accept_file = accept_file or (lambda _, fname: fname.lower() == "readme.md")
    files = []
    for (dirpath, dirnames, filenames) in os.walk(root):
        for filename in filenames:
            full_name = os.path.join(dirpath, filename)
            if not accept_file(dirpath, filename) or gitaware.is_ignored(full_name):
                continue
            files.append(full_name)
        dirnames[:] = filter(lambda d: d != ".git", dirnames)
    return files


def _pretty_option(root, file, is_selected):
    rel_path = os.path.relpath(file, root)
    return f"[{'x' if is_selected else ' '}] {rel_path}"


def offer_to_index(git_root):
    if _is_processed(git_root):
        return

    print("  👀 detected git repository at", git_root)
    feedback.feedback({"event": "git_repo_detected"})
    with loading_animation(Simple("checking for README files... [ctrl+c] cancel")):
        try:
            files = _discover_indexable_files(git_root)
        except KeyboardInterrupt:
            feedback.feedback({"event": "git_repo_cancelled"})
            _set_processed(git_root)
            print("  checking for README files cancelled, will not attempt to index this repository again")
            return
    _set_processed(git_root)
    feedback.feedback({"event": "indexable_files", "count": len(files)})
    if len(files) == 0:
        return
    selected = [False] * len(files)

    def make_file_options():
        return [_pretty_option(git_root, f, s) for (f, s) in zip(files, selected)]

    def toggle_selection(index):
        if index >= len(files):
            # don't toggle the global options
            return
        selected[index] = not selected[index]
        ui.reset_options(make_file_options() + global_options, is_loading=False)

    global_options = ["Accept all", "Reject all"]
    all_options = make_file_options() + global_options

    ui = selections.UI(
        all_options,
        is_loading=False,
        actions={
            " ": lambda _, ui: toggle_selection(ui.selected),
        },
        header="  use the following files to help answer questions about this repository?",
        footer=" ".join([
            selections.FOOTER_SECTIONS["select"],
            f"{colorama.Style.BRIGHT}[space]{colorama.Style.RESET_ALL} toggle",
            selections.FOOTER_SECTIONS["confirm"],
            selections.FOOTER_SECTIONS["cancel"]
        ])
    )
    ui.select(len(files))  # default to Accept All
    index = ui.input()
    if index == len(files):
        selected = [True] * len(files)
    elif index == len(files) + 1:
        selected = [False] * len(files)
    if index >= len(files):
        ui._is_active = True
        ui.reset_options(make_file_options() + global_options, is_loading=False)
        ui._is_active = False

    feedback.feedback({"event": "indexable_files_selected", "total": len(files), "selected": sum(selected)})
    print()

    store = index_store.IndexStore(os.path.expanduser(settings.user_index_root))
    indexed_files = {item.item_location for item in store.metadata if item.item_type == "file"}
    for (file, is_selected) in zip(files, selected):
        if is_selected:
            print("indexing:", os.path.relpath(file, git_root))
            if file not in indexed_files:
                meta, db = content.index_file(file)
                store.add_or_update(meta, db)
            else:
                print("  already indexed")

    return
