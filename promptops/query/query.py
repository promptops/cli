import json
import logging
import os
import sys
from dataclasses import dataclass
from copy import copy
import subprocess
import threading
import random
from typing import Optional, List, Tuple

import colorama
import requests
from prompt_toolkit import print_formatted_text
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.formatted_text import HTML, to_formatted_text
from promptops.shells import get_shell

from promptops import settings
from promptops import trace
from promptops import user
from promptops.ui import prompts
from promptops.ui import selections
from promptops.loading import Simple, loading_animation
from promptops import similarity
from promptops import corrections
from promptops.corrections import get_correction
from promptops.feedback import feedback
from promptops import history
from promptops import scrub_secrets
from promptops import shells
from promptops.index import index_store
from promptops import gitaware
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


def printer(pipe, func):
    for line in iter(pipe.readline, b''):
        line_decoded = line.decode()
        sys.stdout.write(line_decoded)
        sys.stdout.flush()
        func(line)
    pipe.close()


def run(cmd: Result) -> (int, Optional[str]):
    if cmd.lang == "shell":
        process = subprocess.Popen(
            cmd.script, shell=True, start_new_session=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout = []
        stderr = []

        thread_out = threading.Thread(target=printer, args=[process.stdout, lambda line: stdout.append(line.decode())])
        thread_err = threading.Thread(target=printer, args=[process.stderr, lambda line: stderr.append(line.decode())])

        thread_out.start()
        thread_err.start()
        thread_out.join()
        thread_err.join()

        sys.stdout.write("\n")
        sys.stdout.flush()

        process.wait()
        get_shell().add_to_history(cmd.script)
        history.add(scrub_secrets.scrub_line(".bash_history", cmd.script), process.returncode)

        return process.returncode, "".join(stderr)
    else:
        raise NotImplementedError(f"{cmd.lang} not implemented yet")


def corrections_search(embedding):
    db = corrections.get_db()
    similar = db.search(embedding, k=3, min_similarity=0.8)
    return list(filter(lambda c: c[0].corrected is not None,
                       [(corrections.QATuple.from_dict(s), score) for s, score in similar]))


def search_indexed_fragments(embedding, current_dir: str) -> list[index_store.SearchResult]:
    store = index_store.IndexStore(os.path.expanduser(settings.user_index_root))

    def accept_source(meta: index_store.ItemMetadata):
        if meta.item_type != "file":
            return True
        dirname = os.path.dirname(meta.item_location)
        return current_dir.startswith(dirname)

    similar = store.search(embedding, k=3, min_similarity=0.7, accept_source=accept_source)
    return similar


def make_revise_option():
    return "\x1b[3m💭️ don't see what you're looking for? try providing more context\x1b[0m"


<<<<<<< HEAD
def make_show_all_option():
    return "\x1b[3m💭️ see all results \x1b[0m"


ORIGIN_SYMBOLS = {"history": "📖", "promptops": "✨", "curated": "📚", "workflows": " 🧰"}
=======
ORIGIN_SYMBOLS = {"history": "📖", "promptops": "✨", "curated": "📚", "workflows": "tbd"}
>>>>>>> 044c398 (workflows: slightly modify ux flow for saving recipes)


def ellipsis_if_needed(text, max_width, more="..."):
    if len(text) <= max_width:
        return text
    return text[:max_width - len(more)] + more


def pretty_result(result: Result):
    text = result.script if result.lang != "text" else colorama.Fore.YELLOW + ellipsis_if_needed(result.script, 120,
                                                                                                 "...") + colorama.Style.RESET_ALL
    return (ORIGIN_SYMBOLS.get(result.origin, f"[{result.origin[0]}]") + " " if result.origin else "") + text


def sort_results(results: List[Result]):
    return sorted(results, key=lambda x: x.score)


def set_results(primary, secondary, results) -> Tuple[List[Result], List[Result]]:

    if not results or len(results) == 0:
        return primary, secondary

    results = sort_results(results)

    primary.append(results.pop(0))
    secondary.extend(results)

    # we don't sort primary to not have the ui jump around
    return primary, sort_results(secondary)


@dataclass
class ConfirmResult:
    result: Result = None
    confirmed: str = ""
    question: str = None
    options: list = None


MINIMUM_DESIRED_RESULTS = 1


def revise_loop(questions: list[str], prev_results: list[list[str]], history_context: list[str]) -> ConfirmResult:
    embedding = similarity.embedding(text="\n".join(questions))
    update_lock = threading.Lock()
    corrected_results = []

    similar_corrections = corrections_search(embedding)
    logging.debug("found %d similar corrections", len(similar_corrections))
    if len(similar_corrections) > 0:
        for qa, score in similar_corrections:
            logging.debug(f"- {score:.2f}: {qa.question} -> {qa.corrected}")
            corrected_results.append(Result(script=qa.corrected, origin="history"))

    history_results = history.check_history(embedding)
    logging.debug("found %d similar history results", len(history_results))
    if len(history_results) > 0:
        for r, score in history_results:
            logging.debug(f"- {score:.2f}: {r}")
    history_results = [
        Result(score=score, script=r if isinstance(r, str) else r["cmd"], explanation="loaded from shell history",
               origin="history")
        for r, score in history_results
    ]

    history_results = sort_results(history_results)
    results = corrected_results + [history_results.pop(0)] if len(history_results) > 0 else []
    secondary = history_results[1:]
    results = deduplicate(results)

    relevant_indexed_data = search_indexed_fragments(embedding, os.getcwd())
    if len(relevant_indexed_data) > 0:
        print("  found information that might be relevant to your question in:")
        printed = set()
        for r in relevant_indexed_data:
            if r.item.item_location in printed:
                continue
            print(f"  ● {r.item.item_location}")
            printed.add(r.item.item_location)
        print()

    ui = None
    tasks = [
        ReturningThread(
            query,
            kwargs=dict(
                q=questions[-1],
                prev_questions=questions[:-1],
                corrected_results=[qa for qa, _ in similar_corrections],
                prev_results=prev_results,
                similar_history=[r.script for r in history_results],
                history_context=history_context,
                relevant_indexed_data=relevant_indexed_data,
            ),
            daemon=True,
        ),
        ReturningThread(
            curated,
            kwargs=dict(
                q=questions[-1],
            ),
            daemon=True,
        ),
        ReturningThread(
            check_workflows,
            kwargs=dict(
                q=questions[-1],
            ),
            daemon=True,
        )
    ]
    num_running = len(tasks)
    show_all = False

    def add_trailing_option(options):
        nonlocal num_running, secondary, show_all
        if num_running > 0:
            return options
        if show_all or len(secondary) == 0:
            show_all = show_all or len(secondary) == 0
            return options + [make_revise_option()]
        else:
            return options + [make_show_all_option()]

    def update_results(extra):
        with update_lock:
            nonlocal num_running, results, secondary, ui, show_all
            num_running -= 1

            results, secondary = set_results(results, secondary, extra)
            if show_all:
                results.extend(secondary)
                secondary = []

            options = [pretty_result(r) for r in deduplicate(results)]
            options = add_trailing_option(options)
            if num_running == 0:
                if len(results) == 0:
                    feedback({"event": "no-results"})
                    print("couldn't find any results, try rephrasing your question or providing more context")
                    selected = prompts.confirm_clarify("")
                    if selected == prompts.EXIT:
                        raise KeyboardInterrupt()
                    return ConfirmResult(question=selected, options=[])
                else:
                    if len(results) < 2:
                        size = len(results)
                        results += secondary[:(MINIMUM_DESIRED_RESULTS - size)]
                        secondary = secondary[(MINIMUM_DESIRED_RESULTS - size):]
            if ui:
                ui.reset_options(options, is_loading=num_running > 0)
            else:
                ui = selections.UI(
                    options,
                    num_running > 0,
                    loading_text=random.choice(messages.QUERY),
                    actions={
                        "\x08": remove_entry,
                        "\x7F": remove_entry,
                    },
                )

    def done_callback(thread: ReturningThread):
        try:
            update_results(thread.result())
        except Exception as exc:
            import traceback
            stack_trace = traceback.format_exc()
            feedback({"event": "unhandled_exception", "error": stack_trace})
            with update_lock:
                nonlocal num_running
                num_running -= 1
                if ui.is_active:
                    ui.clear()
                print("hit exception:", exc)
                if ui.is_active:
                    ui.add_options([], is_loading=num_running > 0)

    for task in tasks:
        task.add_done_callback(done_callback)
        task.start()

    def remove_entry(_, ui: selections.UI):
        with update_lock:
            if ui.selected >= len(results):
                return
            result = results[ui.selected]
            if result.origin == "history":
                results.pop(ui.selected)
                options = [pretty_result(r) for r in results]
                options = add_trailing_option(options)
                ui.reset_options(options, is_loading=num_running > 0)
        hdb = history.get_history_db()
        for item in hdb.objects:
            if isinstance(item, dict) and item["cmd"] == result.script:
                item["ignore"] = True
        hdb.save(os.path.expanduser(settings.history_db_path))

    while True:
        with update_lock:
            options = [pretty_result(r) for r in results]
            options = add_trailing_option(options)

            if ui:
                ui.reset_options(options, is_loading=num_running > 0)
            else:
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
            if show_all:
                selected = prompts.confirm_clarify("")
                if selected == prompts.GO_BACK:
                    continue
                elif selected == prompts.EXIT:
                    raise KeyboardInterrupt()
                return ConfirmResult(question=selected, options=[r.script for r in results if r.origin == "promptops"])
            else:
                show_all = True
                results = deduplicate(results + secondary)
                ui = selections.UI(options, is_loading=num_running > 0, loading_text=random.choice(messages.QUERY))
        else:
            selected = results[index]
            if selected.lang == "text":
                print_formatted_text(selected.script)
                print()
                selected = prompts.confirm_clarify("")
                if selected == prompts.GO_BACK:
                    continue
                elif selected == prompts.EXIT:
                    raise KeyboardInterrupt()
                return ConfirmResult(question=selected,
                                     options=[r.script for r in results if r.origin == "promptops"])
            elif selected.explanation:
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
                            history_context=history_context,
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
        f"It looks like the command failed, would you like us to attempt to fix it using the stderr output?"
    )
    if selected == prompts.GO_BACK:
        return None
    elif selected == prompts.EXIT:
        raise KeyboardInterrupt()

    with loading_animation(Simple("thinking...")):
        ce_task = ReturningThread(target=get_correction, kwargs=dict(prompt=prompt, command=command, error=error), daemon=True)
        ce_task.start()
        result = ce_task.join()

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
    if git_root := gitaware.git_root():
        from .git_repo import offer_to_index
        offer_to_index(git_root)

    question = question.strip()
    questions = [question]
    prev_results = []

    print()

    def input_loop():
        history_context = shells.get_shell().get_recent_history(
            settings.history_context) if settings.history_context else []
        while True:
            results = revise_loop(questions, prev_results, history_context)
            if results.result:
                return results.result, results.confirmed
            else:
                print()
                feedback({"event": "revise"})
                questions.append(results.question)
                prev_results.append(results.options)

    try:
        cmd, confirmed = input_loop()
    except KeyboardInterrupt:
        feedback({"event": "cancelled"})
        return

    if cmd.lang == "text":
        return

    if confirmed:
        # the user corrected the script
        db = corrections.get_db()
        q = "\n".join(questions)
        vector = similarity.embedding(text=q)
        db.update_or_add(vector, corrections.QATuple(question=q, answer=cmd.script, corrected=confirmed).to_dict(),
                         equals=lambda a, b: a["question"] == b["question"])
        logging.debug("added correction to db")
        db.save(os.path.expanduser(settings.corrections_db_path))
        feedback({"event": "corrected"})

    revised_cmd = copy(cmd)
    rc, stderr = 0, ""
    feedback({"event": "run"})

    if cmd.scripts:
        print()
        ui = selections.UI(cmd.scripts + ["exit"], is_loading=False)
        selection = ui.input()
        while selection != len(cmd.scripts):
            revised_cmd = copy(cmd)
            revised_cmd.script = cmd.scripts[selection]
            revised_cmd.script = confirmed
            rc, stderr = run(revised_cmd)

            ui = selections.UI(cmd.scripts + ["exit"], is_loading=False)
            selection = ui.input()
    else:
        revised_cmd.script = confirmed
        rc, stderr = run(revised_cmd)
    feedback({"event": "finished", "rc": rc})

    while rc != 0:
        corrected_cmd = correction_loop("\n".join(questions), revised_cmd.script, stderr)
        if not corrected_cmd:
            return
        feedback({"event": "run"})
        rc, stderr = run(corrected_cmd)
        if rc == 0:
            db = corrections.get_db()
            q = "\n".join(questions)
            vector = similarity.embedding(text=q)
            db.update_or_add(vector, corrections.QATuple(question=q, answer=cmd.script,
                                                         corrected=corrected_cmd.script).to_dict(),
                             equals=lambda a, b: a["question"] == b["question"])
            logging.debug("added correction to db")
            db.save(os.path.expanduser(settings.corrections_db_path))
        feedback({"event": "finished", "rc": rc, "corrected": True})


def query(
        *,
        q: str,
        prev_questions: list[str],
        prev_results: list[list[str]],
        corrected_results: list[corrections.QATuple],
        history_context: list[str],
        similar_history: list[str],
        relevant_indexed_data: list[index_store.SearchResult],
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
            "user_data": [
                {
                    "source_type": r.item.item_type,
                    "source": r.item.item_location,
                    "fragment": r.fragment.fragment,
                } for r in relevant_indexed_data
            ]
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
        logging.debug("no suggestions in response: %s", json.dumps(data, indent=2))

    try:
        message = data.get("message")
    except KeyError:
        message = "-"
        logging.debug("no message in response: %s", json.dumps(data, indent=2))

    return [Result(script=message, lang="text", explanation="-", score=1)]


def curated(*, q: str) -> list[Result]:
    req = {
        "query": q,
        "trace_id": trace.trace_id,
        "platform": sys.platform,
        "shell": os.environ.get("SHELL"),
    }
    logging.debug("curated query with request: %s", req)
    response = requests.post(
        settings.endpoint + "/curated",
        json=req,
        headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
        },
    )
    if response.status_code != 200:
        return []

    data = response.json()
    try:
        return [content_to_result(entry["content"], entry["score"]) for entry in data["items"] if
                entry["score"] >= 0.75]
    except KeyError:
        logging.debug("no suggestions in response: %s", json.dumps(data, indent=2))

    try:
        message = data["message"]
        return [Result(script=message, lang="text", explanation="-")]
    except KeyError:
        logging.debug("no message in response: %s", json.dumps(data, indent=2))
        return []


def content_to_result(content, score) -> Result:
    return Result(
        script=content["content"],
        lang="shell",
        origin="curated",
        score=score,
    )


def check_workflows(*, q: str) -> list[Result]:
    req = {
        "query": q,
        "trace_id": trace.trace_id,
    }
    logging.debug("curated query with request: %s", req)
    response = requests.post(
        settings.endpoint + "/workflows/search",
        json=req,
        headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
        },
    )
    if response.status_code != 200:
        logging.debug("error searching workflows: %s", json.dumps(response, indent=2))
        return []

    data = response.json().get("results", [])

    try:
        return [workflow_to_result(wf) for wf in data]
    except KeyError:
        logging.debug("no suggestions in response: %s", json.dumps(data, indent=2))

    return []


def workflow_to_result(workflow) -> Result:
    return Result(
        scripts=workflow.get("commands", []),
        script=", ".join(workflow.get("commands", [])),
        lang="shell",
        origin="workflows",
        explanation="Detected workflow for: " + workflow.get("description", ""),
        score=workflow.get("score")
    )


def check_workflows(*, q: str) -> list[Result]:
    print("workflows")
    req = {
        "query": q,
        "trace_id": trace.trace_id,
    }
    logging.debug("curated query with request: %s", req)
    response = requests.post(
        settings.endpoint + "/workflows/search",
        json=req,
        headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
        },
    )
    if response.status_code != 200:
        # this exception completely destroys the ui
        return []
        # raise Exception(f"there was problem with the response, status: {response.status_code}, text: {response.text}")

    data = response.json().get("results", [])
    print(len(data))

    if len(data) > 2:
        data = data[:2]

    try:
        return [workflow_to_result(wf) for wf in data]
    except KeyError:
        logging.debug("no suggestions in response: %s", json.dumps(data, indent=2))

    return []


def workflow_to_result(workflow) -> Result:
    return Result(
        script=" && ".join(workflow.get("commands", [])).strip(),
        lang="shell",
        origin="workflows",
        explanation="Detected workflow for: " + workflow.get("description", "")
    )
