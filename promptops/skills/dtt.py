import logging
import os.path
import shlex
import subprocess
import sys

import colorama

from promptops.skills.commit_message import get_commit_message
from promptops.gitaware.commits import get_latest_commits, get_staged_files, get_unstaged_files, get_staged_changes
from promptops.loading import loading_animation
from promptops.loading.simple import Simple
from promptops.ui import selections
from promptops.gitaware.project import git_root

from .choice import Choice


def entry_point():
    # check if there's input from stdin
    if not sys.stdin.isatty():
        contents = sys.stdin.read()
        if is_diff(contents) > 0.8:
            print("detected git diff")
            pick_commit_message(contents)
            sys.exit(0)

    while True:
        options = []
        if root := git_root():
            cwd = os.getcwd()
            if files := get_staged_files():
                logging.debug("discovered staged changes: %s", files)
                files = [os.path.relpath(os.path.join(root, f), cwd) for f in files]
                options.append(Choice("commit_staged", f"Commit staged changes [{len(files)} files]", {"files": files}))
            if files := get_unstaged_files():
                logging.debug("discovered unstaged changes: %s", files)
                files = [os.path.relpath(os.path.join(root, f), cwd) for f in files]
                options.append(Choice("add_unstaged", f"Add changes to staging area [{len(files)} files]", {"files": files}))
        options.append(Choice("query", "Ask a question", {}))
        ui = selections.UI([choice.text for choice in options], header="Did you mean to...", is_loading=False)
        selected = ui.input()
        if selected is not None:
            print()
            handle(options[selected])
            print()
        else:
            sys.exit(0)


def pick_commit_message(diff: str):
    with loading_animation(Simple("Generating commit message...")):
        options = get_commit_message(diff, get_latest_commits(n=10))

    sys.stdin = open("/dev/tty")
    ui = selections.UI(options, is_loading=False)
    selected = ui.input()
    if selected is not None:
        print(options[selected])


def is_diff(contents: str) -> float:
    """return the probability of the contents being a diff"""
    lines = contents.splitlines()
    if len(lines) < 2:
        return 0.0
    if lines[0].startswith("diff --git"):
        return 1.0


def handle(choice: Choice):
    if choice.id == "commit_staged":
        commit_staged(**choice.parameters)
    elif choice.id == "add_unstaged":
        add_unstaged(**choice.parameters)
    elif choice.id == "query":
        print("let's query here, prompt and stuff")


def add_unstaged(files: list[str]):
    files = sorted(files)
    extra_options = ["Add all"]
    selected_files = [False] * len(files)

    def _pretty_option(file, is_selected):
        return f"[{'x' if is_selected else ' '}] {file}"

    def make_file_options():
        return [_pretty_option(file, is_selected) for file, is_selected in zip(files, selected_files)]

    def toggle_selection(index):
        if index >= len(files):
            # don't toggle the global options
            return
        selected_files[index] = not selected_files[index]
        ui.reset_options(make_file_options() + extra_options, is_loading=False)

    def view_diff(index):
        if index >= len(files):
            subprocess.call(["git", "diff"])
        else:
            file_name = files[index]
            subprocess.call(["git", "diff", file_name])

    ui = selections.UI(
        make_file_options() + extra_options,
        is_loading=False,
        actions={
            " ": lambda _, ui: toggle_selection(ui.selected),
            "d": lambda _, ui: view_diff(ui.selected),
        },
        header="  select files to add to staging area",
        footer=" ".join([
            selections.FOOTER_SECTIONS["select"],
            f"{colorama.Style.BRIGHT}[space]{colorama.Style.RESET_ALL} toggle",
            f"{colorama.Style.BRIGHT}[d]{colorama.Style.RESET_ALL} view diff",
            selections.FOOTER_SECTIONS["confirm"],
            selections.FOOTER_SECTIONS["cancel"]
        ])
    )
    ui.select(len(files))
    index = ui.input()
    if index == len(files):
        selected_files = [True] * len(files)
    if index >= len(files):
        ui._is_active = True
        ui.reset_options(make_file_options() + extra_options, is_loading=False)
        ui._is_active = False
    cmd = ["git", "add"] + [file for file, is_selected in zip(files, selected_files) if is_selected]
    print(shlex.join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        print(f"git commit failed with return code {rc}")


def commit_staged(files: list[str]):
    print("staged changes")
    for file in files:
        print(f"  {file}")
    print()

    diff = get_staged_changes()
    if diff is None or len(diff) == 0:
        print("no changes")
        return

    with loading_animation(Simple("Generating commit message...")):
        options = get_commit_message(diff, get_latest_commits(n=10))

    ui = selections.UI(options, header="select commit message to use", is_loading=False)
    selected = ui.input()
    if selected is not None:
        print(options[selected])

    cmd = ["git", "commit", "-e", "-m", options[selected]]
    print(shlex.join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        print(f"git commit failed with return code {rc}")
