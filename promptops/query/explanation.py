import logging
import time
import random

import requests
import colorama

from promptops import corrections
from .dtos import Result
import threading
from promptops.loading import Simple
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import HTML, to_formatted_text
from typing import Callable
from promptops import settings
from promptops.user import user_id
from promptops.trace import trace_id
from . import messages
from promptops import scrub_secrets


def get_explanation(
    *,
    result: Result,
    prev_questions: list[str],
    prev_results: list[list[str]],
    corrected_results: list[corrections.QATuple],
    history_context: list[str],
    similar_history: list[str],
):
    response = requests.post(
        settings.endpoint + "/explain",
        json={
            "script": result.script,
            "lang": result.lang,
            "questions": prev_questions,
            "results": prev_results,
            "context": {
                "history": history_context,
                "corrections": [
                    (qa.question, scrub_secrets.scrub_line("~/.bash_history", qa.corrected)) for qa in corrected_results
                ],
                "similar": similar_history,
            },
            "trace_id": trace_id,
        },
        headers={
            "user-agent": f"promptops-cli; user_id={user_id()}",
        },
    )
    response.raise_for_status()
    data = response.json()
    logging.debug(f"explanation response: {data}")
    return data["explanation"]


class ReturningThread(threading.Thread):
    def __init__(self, target, args=None, kwargs=None, daemon=False):
        super().__init__(target=self.run, daemon=daemon)
        self._return_value = None
        self._exception = None
        self._finished = False
        self.function = target
        self.args = args or []
        self.kwargs = kwargs or {}
        self._done_callbacks = []

    def run(self):
        try:
            self._return_value = self.function(*self.args, **self.kwargs)
        except Exception as e:
            self._exception = e
        self._finished = True
        for fn in self._done_callbacks:
            fn(self)

    def join(self, timeout=None) -> any:
        super().join(timeout)
        if self._exception is not None:
            raise self._exception
        return self._return_value

    def add_done_callback(self, fn):
        self._done_callbacks.append(fn)

    def result(self):
        if not self._finished:
            raise RuntimeError("not finished")
        if self._exception is not None:
            raise self._exception
        return self._return_value


def _loading_animation(spinner, should_continue: Callable[[], bool]):
    while should_continue():
        spinner.step()
        time.sleep(0.1)


def explain(
    *,
    result: Result,
    prev_questions: list[str],
    prev_results: list[list[str]],
    corrected_results: list[corrections.QATuple],
    history_context: list[str],
    similar_history: list[str],
):

    is_loading = True
    msg = random.choice(messages.EXPLAIN)
    spinner = Simple(f"{msg} {colorama.Style.BRIGHT}[ctrl+c]{colorama.Style.RESET_ALL} cancel")
    loading_thread = threading.Thread(
        target=_loading_animation,
        args=(
            spinner,
            lambda: is_loading,
        ),
        daemon=True,
    )
    loading_thread.start()

    t = ReturningThread(
        target=get_explanation,
        args=[],
        kwargs=dict(
            result=result,
            prev_questions=prev_questions,
            prev_results=prev_results,
            corrected_results=corrected_results,
            history_context=history_context,
            similar_history=similar_history,
        ),
        daemon=True,
    )
    t.start()

    try:
        explanation = t.join()
    except requests.HTTPError as e:
        is_loading = False
        spinner.clear()
        print_formatted_text(HTML(f"<ansired> │  oh snap, failed to fetch you the explanation: {e}</ansired>"))
        print()
        return
    finally:
        if is_loading:
            is_loading = False
            spinner.clear()

    indented = "\n".join(" │  " + line for line in explanation.splitlines())
    print_formatted_text(to_formatted_text(HTML(indented), style="fg: ansiyellow"))
    print()
