import logging
import os.path
import shlex
import subprocess
import sys
import threading
from dataclasses import dataclass

import colorama
import prompt_toolkit
from prompt_toolkit.formatted_text import HTML

from promptops.skills.commit_message import get_commit_message
from promptops.gitaware.commits import get_latest_commits, get_staged_files, get_unstaged_files, get_staged_changes
from promptops.loading import loading_animation
from promptops.loading.simple import Simple
from promptops.ui import selections, prompts
from promptops.gitaware.project import git_root
from promptops.feedback import feedback
from promptops.query.explanation import ReturningThread
from .next import instant_choices, generated_choices
from .choice import Choice


@dataclass
class Counter:
    value: int


def entry_point():
    print()
    # check if there's input from stdin
    if not sys.stdin.isatty():
        contents = sys.stdin.read()
        if is_diff(contents) > 0.8:
            feedback({"event": "stream_diff"})
            sys.stderr.write("detected git diff\n")
            pick_commit_message(contents)
            return
        else:
            sys.stderr.write("supported input types: git diff")
            sys.stderr.write("example: git diff | um")

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

        options.extend(instant_choices(3))
        options.append(Choice("query", "Ask a question", {}))

        tasks = [
            ReturningThread(generated_choices, daemon=True),
        ]
        num_running = Counter(len(tasks))
        update_lock = threading.Lock()

        ui = selections.UI([choice.text for choice in options], header="🤔 did you mean to...", is_loading=num_running.value > 0)
        for task in tasks:
            task.add_done_callback(done_callback(update_lock, ui, options, num_running))
            task.start()
        selected = ui.input()
        print()
        try:
            handle(options[selected])
            print()
        except KeyboardInterrupt:
            pass


def done_callback(lock, ui: selections.UI, options: list[Choice], counter: Counter):
    def inner(thread: ReturningThread):
        try:
            with lock:
                counter.value -= 1
                options.extend(thread.result())
                if ui.is_active:
                    ui.reset_options([option.text for option in options], is_loading=counter.value > 0)
        except Exception as exc:
            logging.exception(exc)

    return inner


def pick_commit_message(diff: str):
    with loading_animation(Simple("Generating commit message...", stream=sys.stderr)):
        options = get_commit_message(diff, get_latest_commits(n=10))

    sys.stdin = open("/dev/tty")
    if len(options) > 0:
        print(options[0])
    else:
        sys.stderr.write("failed to generate commit message")
        sys.exit(1)


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
        for i in range(2):
            if i > 0:
                print("please enter a question")
            bottom_toolbar = HTML("<b>[enter]</b> confirm <b>[ctrl+c]</b> exit")
            # get the name of the calling script
            alias = os.path.basename(sys.argv[0])
            question = prompt_toolkit.prompt(f"{alias}: ", bottom_toolbar=bottom_toolbar)
            question = question.strip()
            if question != "":
                from promptops.query.query import do_query
                do_query(question)
                break
        else:
            print("no question entered")
        return
    elif choice.id == "command":
        script = choice.parameters["option"]
        confirmed = prompts.confirm_command(script, False)
        if confirmed == prompts.GO_BACK:
            return
        elif confirmed == prompts.EXIT:
            return
        from promptops.query.query import Result
        from promptops.query.query import run
        run(Result(script=script, origin=choice.parameters["origin"]))


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

    def open_diff():
        subprocess.call(["git", "diff", "--staged"])

    ui = selections.UI(
        options,
        header="select commit message to use",
        is_loading=False,
        actions={
            "d": lambda _, __: open_diff()
        }, footer=" ".join([
            selections.FOOTER_SECTIONS["select"],
            f"{colorama.Style.BRIGHT}[d]{colorama.Style.RESET_ALL} view diff",
            selections.FOOTER_SECTIONS["confirm"],
            selections.FOOTER_SECTIONS["cancel"]
        ])
    )
    selected = ui.input()
    print(options[selected])

    cmd = ["git", "commit", "-e", "-m", options[selected]]
    print(shlex.join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        print(f"git commit failed with return code {rc}")
