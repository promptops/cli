import copy
import math
import sys
import os

from promptops.ui.selections import UI, FOOTER_SECTIONS
import colorama
import threading
import pyperclip


def copy_text():
    colorama.init()

    print("testing")

    options = ["confirm defaults", "change"]

    def copy_action(_, ui):
        flash_options = copy.copy(options)
        selected = ui.selected
        flash_options[selected] = "\x1b[7m" + "copied!" + colorama.Style.RESET_ALL
        pyperclip.copy(options[selected])
        ui.reset_options(flash_options, ui.is_loading)

        def revert():
            ui.reset_options(options, ui.is_loading)

        t = threading.Timer(0.5, revert)
        t.start()

    ui = UI(
        options=["confirm defaults", "change"],
        is_loading=False,
        footer=" ".join(
            [FOOTER_SECTIONS["select"], FOOTER_SECTIONS["confirm"], FOOTER_SECTIONS["copy"], FOOTER_SECTIONS["cancel"]]
        ),
        actions={
            "c": copy_action,
            "C": copy_action,
        },
    )

    selection = ui.input()
    print("selected", selection)


def remove_text():
    colorama.init()

    print("testing")

    options = ["option1", "option2", "option3", "option4", "option5", "option6", "option7", "option8"]

    def remove_item(_, ui):
        selected = ui.selected
        result = options.pop(selected)
        ui.reset_options(options, ui.is_loading)

    ui = UI(
        options=options,
        is_loading=False,
        footer=" ".join(
            [FOOTER_SECTIONS["select"], FOOTER_SECTIONS["confirm"], FOOTER_SECTIONS["copy"], FOOTER_SECTIONS["cancel"]]
        ),
        actions={
            "\x08": remove_item,
            "\x7F": remove_item,
        },
    )

    selection = ui.input()
    print("selected", selection)


def stream_async():
    from prompt_toolkit import PromptSession
    from prompt_toolkit.patch_stdout import patch_stdout
    import asyncio
    import os

    async def print_in_background():
        counter = 0
        lines_written = 0
        text = ""
        cols, rows = os.get_terminal_size()
        print("rows", rows, "cols", cols)
        while True:
            text += f"Counter: {counter}"
            expression = text + "\n"
            if lines_written > 0:
                expression = f"\x1b[{lines_written}A\x1b[K" + expression
            sys.stdout.write(expression)
            counter += 1
            lines_written = int(math.ceil(len(text) / cols))
            await asyncio.sleep(1)  # wait for 1 second

    async def get_input():
        task = asyncio.create_task(print_in_background())
        session = PromptSession()
        result = await session.prompt_async("Enter something: ")
        task.cancel()
        print("You said: ", result)

    with patch_stdout(raw=True):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(get_input())


def update_async_simple():
    from prompt_toolkit import PromptSession
    from prompt_toolkit.patch_stdout import patch_stdout
    from promptops.loading import Simple, loading_animation
    from promptops.query.explanation import ReturningThread
    import threading
    import time

    colorama.init()

    loaded = threading.Event()

    def fetch_explanation():
        time.sleep(5)
        try:
            return "somthing " * 20
        finally:
            loaded.set()

    def confirm_prompt():
        session = PromptSession()
        try:
            return session.prompt("\nEnter something: ")
        finally:
            loaded.set()

    with patch_stdout(raw=True):
        sys.stdout.sleep_between_writes = 0.2
        explain_task = ReturningThread(target=fetch_explanation, daemon=True)
        prompt_task = ReturningThread(target=confirm_prompt, daemon=True)
        with loading_animation(Simple(""), fps=5):
            explain_task.start()
            prompt_task.start()
            loaded.wait()
        if not explain_task.is_alive():
            explanation = explain_task.join()
            print(explanation)
        sys.stdout.sleep_between_writes = 0.5
        confirmed = prompt_task.join()
        print("You said: ", confirmed)


def scroll():
    size = os.get_terminal_size()
    print("size", size)
    input("press enter to continue")
    options = [f"option-{i}" for i in range(100)]
    ui = UI(options=options, is_loading=True, header="hello world")
    selected = ui.input()
    print("selected", selected)


if __name__ == "__main__":
    # stream_async()
    # update_async_simple()
    # remove_text()
    scroll()
