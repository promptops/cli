import logging
import os
import sys
from dataclasses import dataclass
from copy import copy
import subprocess
import threading
import random
from typing import Optional

import requests
from prompt_toolkit import print_formatted_text
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.formatted_text import HTML, to_formatted_text
import prompt_toolkit

from promptops import settings
from promptops import trace
from promptops import user
from promptops.ui import prompts
from promptops.ui import selections
from promptops.cancellable import ThreadPoolExecutor
from promptops.loading import Simple, loading_animation
from promptops import similarity
from promptops import corrections
from promptops.corrections import get_correction
from promptops.feedback import feedback
from promptops import history
from promptops import settings_store
from promptops import scrub_secrets
from .dtos import Result
from .explanation import get_explanation, ReturningThread
from . import messages


def deduplicate(results: list[Result]):
    results_set = set()
    final_results = []
    for result in results:
        if result.script in results_set:
            continue
        results_set.add(result.script)
        final_results.append(result)
    return final_results


def run(cmd: Result) -> (int, Optional[str]):
    if cmd.lang == "shell":
        proc = subprocess.run(
            cmd.script, shell=True, start_new_session=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if proc.stdout and str(proc.stdout) != "":
            sys.stdout.write(proc.stdout.decode("utf-8"))
        if proc.stderr and str(proc.stderr) != "":
            sys.stdout.write(proc.stderr.decode("utf-8"))
        sys.stdout.flush()

        history.add(scrub_secrets.scrub_line(".bash_history", cmd.script), proc.returncode)
        return proc.returncode, str(proc.stderr)
    else:
        raise NotImplementedError(f"{cmd.lang} not implemented yet")


def corrections_search(embedding):
    db = corrections.get_db()
    similar = db.search(embedding, k=3, min_similarity=0.8)
    return [(corrections.QATuple.from_dict(s), score) for s, score in similar]


def make_revise_option():
    return "\x1b[3m💭️ don't see what you're looking for? try providing more context\x1b[0m"


ORIGIN_SYMBOLS = {"history": "📖", "promptops": "✨"}


def pretty_result(result: Result):
    return (ORIGIN_SYMBOLS.get(result.origin, f"[{result.origin[0]}]") + " " if result.origin else "") + result.script


@dataclass
class ConfirmResult:
    result: Result = None
    confirmed: str = ""
    question: str = None
    options: list = None


def revise_loop(questions: list[str], prev_results: list[list[str]]) -> ConfirmResult:
    embedding = similarity.embedding(text="\n".join(questions))
    with loading_animation(Simple("thinking...")), ThreadPoolExecutor(max_workers=5) as tpe:
        cs_task = tpe.submit(corrections_search, embedding)
        hs_task = tpe.submit(history.check_history, embedding)

    update_lock = threading.Lock()
    corrected_results = []
    similar_corrections = cs_task.result()
    logging.debug("found %d similar corrections", len(similar_corrections))
    if len(similar_corrections) > 0:
        for qa, score in similar_corrections:
            logging.debug(f"- {score:.2f}: {qa.question} -> {qa.corrected}")
            corrected_results.append(Result(script=qa.corrected, origin="history"))
    history_results = hs_task.result()
    logging.debug("found %d similar history results", len(history_results))
    if len(history_results) > 0:
        for r, score in history_results:
            logging.debug(f"- {score:.2f}: {r}")
    history_results = [
        Result(script=r if isinstance(r, str) else r["cmd"], explanation="loaded from shell history", origin="history")
        for r, _ in history_results
    ]

    results = corrected_results + history_results
    results = deduplicate(results)

    tpe = ThreadPoolExecutor(max_workers=2)
    ui = None
    tasks = [
        tpe.submit(
            query,
            q=questions[-1],
            prev_questions=questions[:-1],
            corrected_results=[qa for qa, _ in similar_corrections],
            prev_results=prev_results,
            similar_history=[r.script for r in history_results],
            history_context=[],
        )
    ]
    num_running = len(tasks)

    def update_results(extra):
        with update_lock:
            nonlocal num_running
            num_running -= 1
            # TODO: deduplicate
            results.extend(extra)
            if ui:
                options = [pretty_result(r) for r in results]
                if num_running == 0:
                    options += [make_revise_option()]
                ui.reset_options(options, is_loading=num_running > 0)

    def done_callback(future):
        if future.exception():
            print(future.exception())
        update_results(future.result())

    for task in tasks:
        task.add_done_callback(tpe.cancellable_callback(done_callback))

    if len(results) == 0:
        with loading_animation(Simple("thinking...")):
            tpe.shutdown(wait=True)
        num_running = 0
        results = [r for t in tasks for r in t.result()]
        results = deduplicate(results)
        if len(results) == 0:
            feedback({"event": "no-results"})
            print("couldn't find any results, try rephrasing your question or providing more context")
            selected = prompts.confirm_clarify("")
            if selected == prompts.EXIT:
                raise KeyboardInterrupt()
            return ConfirmResult(question=selected, options=[])

    def remove_entry(_, ui: selections.UI):
        with update_lock:
            if ui.selected >= len(results):
                return
            result = results[ui.selected]
            if result.origin == "history":
                results.pop(ui.selected)
                options = [pretty_result(r) for r in results]
                if num_running == 0:
                    options += [make_revise_option()]
                ui.reset_options(options, is_loading=num_running > 0)
        hdb = history.get_history_db()
        for item in hdb.objects:
            if isinstance(item, dict) and item["cmd"] == result.script:
                item["ignore"] = True
        hdb.save(os.path.expanduser(settings.history_db_path))

    while True:
        with update_lock:
            options = [pretty_result(r) for r in results]
            if num_running == 0:
                options += [make_revise_option()]
            ui = selections.UI(
                options,
                num_running > 0,
                loading_text=random.choice(messages.QUERY),
                actions={
                    "\x08": remove_entry,
                    "\x7F": remove_entry,
                },
            )
        index = ui.input()
        print()
        if index == len(results):
            selected = prompts.confirm_clarify("")
            if selected == prompts.GO_BACK:
                continue
            elif selected == prompts.EXIT:
                raise KeyboardInterrupt()
            return ConfirmResult(question=selected, options=[r.script for r in results if r.origin == "promptops"])
        else:
            selected = results[index]
            if selected.explanation:
                print_formatted_text(HTML(selected.explanation))
                print()
                confirmed = prompts.confirm_command(selected.script, False)
            elif selected.origin == "promptops" and settings.request_explanation:

                done_loading = threading.Event()

                def _explain_and_done(*args, **kwargs):
                    try:
                        return get_explanation(*args, **kwargs)
                    finally:
                        done_loading.set()

                def _confirm_and_done(*args, **kwargs):
                    try:
                        return prompts.confirm_command(*args, **kwargs)
                    finally:
                        done_loading.set()

                with patch_stdout(raw=True):
                    et = ReturningThread(
                        target=_explain_and_done,
                        kwargs=dict(
                            result=selected,
                            prev_questions=questions[:-1],
                            prev_results=prev_results,
                            corrected_results=[qa for qa, _ in similar_corrections],
                            similar_history=[r.script for r in history_results],
                            history_context=[],
                        ),
                        daemon=True,
                    )
                    pt = ReturningThread(
                        target=_confirm_and_done,
                        args=(selected.script, False),
                        kwargs=dict(
                            message="\n> ",
                        ),
                    )
                    msg = random.choice(messages.EXPLAIN)
                    sys.stdout.sleep_between_writes = 0.2
                    with loading_animation(Simple(msg), fps=5):
                        et.start()
                        pt.start()
                        done_loading.wait()
                    sys.stdout.sleep_between_writes = 0.5
                    if not et.is_alive():
                        try:
                            explanation = et.join()
                            indented = "\n".join(" │  " + line for line in explanation.splitlines())
                            print_formatted_text(to_formatted_text(HTML(indented), style="fg: ansiyellow"))
                            print()
                        except requests.HTTPError as e:
                            print_formatted_text(
                                HTML(f"<ansired> │  oh snap, failed to fetch you the explanation: {e}</ansired>")
                            )
                            print()
                    confirmed = pt.join()
            else:
                confirmed = prompts.confirm_command(selected.script, False)

            if confirmed == prompts.GO_BACK:
                continue
            elif confirmed == prompts.EXIT:
                raise KeyboardInterrupt()
            return ConfirmResult(result=selected, confirmed=confirmed)


def correction_loop(prompt: str, command: str, error: str) -> Optional[Result]:
    selected = prompts.confirm(
        f"looks like the command failed (return code was not 0), would you like us to attempt to fix it?"
    )
    if selected == prompts.GO_BACK:
        return None
    elif selected == prompts.EXIT:
        raise KeyboardInterrupt()

    with loading_animation(Simple("thinking...")), ThreadPoolExecutor(max_workers=5) as tpe:
        ce_task = tpe.submit(get_correction, prompt=prompt, command=command, error=error)

    result = ce_task.result()

    results = [
        Result(script=result, explanation=f"Revised previous command: {command}"),
    ]
    options = [pretty_result(r) for r in results]
    ui = selections.UI(options, False, loading_text=random.choice(messages.QUERY))

    index = ui.input()
    selected = results[index]
    if selected == prompts.GO_BACK:
        return None
    elif selected == prompts.EXIT:
        raise KeyboardInterrupt()

    print()
    return selected


def do_query(question: str):
    question = question.strip()
    if question == "":
        feedback({"event": "empty-initial-query"})
        for i in range(2):
            if i > 0:
                print("please enter a question")
            bottom_toolbar = HTML("<b>[enter]</b> confirm <b>[ctrl+c]</b> exit")
            # get the name of the calling script
            alias = os.path.basename(sys.argv[0])
            question = prompt_toolkit.prompt(f"{alias}: ", bottom_toolbar=bottom_toolbar)
            question = question.strip()
            if question != "":
                break
        else:
            print("no question entered")
            sys.exit(0)

    questions = [question]
    prev_results = []

    print()

    def input_loop():
        while True:
            try:
                results = revise_loop(questions, prev_results)
                if results.result:
                    return results.result, results.confirmed
                else:
                    print()
                    feedback({"event": "revise"})
                    questions.append(results.question)
                    prev_results.append(results.options)
            except KeyboardInterrupt:
                print()
                feedback({"event": "cancelled"})
                sys.exit(1)

    try:
        cmd, confirmed = input_loop()
    except KeyboardInterrupt:
        feedback({"event": "cancelled"})
        sys.exit(1)

    if cmd.script != confirmed or len(questions) > 1:
        # the user corrected the script
        db = corrections.get_db()
        q = "\n".join(questions)
        vector = similarity.embedding(text=q)
        db.add(vector, corrections.QATuple(question=q, answer=cmd.script, corrected=confirmed).to_dict())
        logging.debug("added correction to db")
        db.save(os.path.expanduser(settings.corrections_db_path))
        feedback({"event": "corrected"})

    feedback({"event": "run"})
    revised_cmd = copy(cmd)
    revised_cmd.script = confirmed
    rc, stdout = run(revised_cmd)
    feedback({"event": "finished", "rc": rc})

    while rc != 0:
        corrected_cmd = correction_loop("\n".join(questions), revised_cmd.script, stdout)
        if not corrected_cmd:
            return
        rc, stdout = run(corrected_cmd)
        if rc == 0:
            db = corrections.get_db()
            q = "\n".join(questions)
            vector = similarity.embedding(text=q)
            db.add(vector, corrections.QATuple(question=q, answer=cmd.script, corrected=corrected_cmd.script).to_dict())
            logging.debug("added correction to db")
            db.save(os.path.expanduser(settings.corrections_db_path))
        feedback({"event": "finished", "rc": rc, "corrected": True})


def query_mode(args):
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings.model = args.mode
    settings.history_context = args.history_context
    settings.request_explanation = args.explain
    try:
        do_query(" ".join(args.question))
        if settings_store.is_changed():
            for _ in range(3):
                answer = input("save the current settings? [y/n]")
                if answer == "y":
                    settings_store.save()
                    break
                elif answer == "n":
                    break
    except KeyboardInterrupt:
        pass


def query(
    *,
    q: str,
    prev_questions: list[str],
    prev_results: list[list[str]],
    corrected_results: list[corrections.QATuple],
    history_context: list[str],
    similar_history: list[str],
) -> list[Result]:
    req = {
        "query": q,
        "prev_questions": prev_questions,
        "prev_suggestions": prev_results,
        "context": {
            "history": history_context,
            "similar": similar_history,
            "corrections": [
                (qa.question, scrub_secrets.scrub_line("~/.bash_history", qa.corrected)) for qa in corrected_results
            ],
        },
        "model": settings.model,
        "trace_id": trace.trace_id,
        "platform": sys.platform,
        "shell": os.environ.get("SHELL"),
    }
    logging.debug("query with request: %s", req)
    response = requests.post(
        settings.endpoint + "/query",
        json=req,
        headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
        },
    )
    if response.status_code != 200:
        # this exception completely destroys the ui
        return []
        # raise Exception(f"there was problem with the response, status: {response.status_code}, text: {response.text}")

    data = response.json()
    try:
        return [Result.from_dict(entry) for entry in data["suggestions"]]
    except KeyError:
        logging.debug("response: %s", data)
        raise
