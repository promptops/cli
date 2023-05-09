from argparse import ArgumentParser, REMAINDER
from dataclasses import dataclass
import sys
import os

import prompt_toolkit

from promptops.query import query, Result
from promptops import settings
from promptops.shells import get_shell
from promptops.ui import display_prompt, EXIT, GO_BACK, TOGGLE_CLARIFY_MODE, display_clarity_prompt
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import FormattedText, HTML
from concurrent.futures import ThreadPoolExecutor
import subprocess
import time
from promptops.loading import Simple
from copy import copy
from promptops import similarity
from promptops import corrections
from promptops.feedback import feedback
from promptops import settings_store
import logging


@dataclass
class Arguments:
    query: str
    history_context: int
    version: bool


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--config", action="store_true", default=False)
    parser.add_argument("--alias", default="um")
    parser.add_argument("--history-context", dest="history_context", default=0)
    parser.add_argument("--version", action="store_true", default=False, help="print version and exit")
    try:
        split_ix = sys.argv.index("--")
        args = parser.parse_args(sys.argv[1:split_ix])
        q = " ".join(sys.argv[split_ix+1:])
    except ValueError:
        args = parser.parse_args()
        q = ""

    return Arguments(query=q, **args.__dict__)


def deduplicate(results: list[Result]):
    results_set = set()
    final_results = []
    for result in results:
        if result.script in results_set:
            continue
        results_set.add(result.script)
        final_results.append(result)
    return final_results


def load_session(fname: str):
    import json
    import time
    with open(fname) as fp:
        data = json.load(fp)
    if time.time() - data["created"] > 10 * 60:
        raise ValueError("session too old")
    return data["session_id"]


def store_session(fname: str, session_id: str):
    import json
    import time
    with open(fname, "w") as fp:
        json.dump({
            "session_id": session_id,
            "created": time.time()
        }, fp)


def run(cmd: Result) -> int:
    if cmd.lang == "shell":
        proc = subprocess.run(cmd.script, shell=True, start_new_session=True)
        return proc.returncode
    else:
        raise NotImplementedError(f"{cmd.lang} not implemented yet")


def run_confirm_loop(q: str, result: Result) -> Result:
    clarify_mode = False

    expression = result.script
    if result.explanation is not None:
        print_formatted_text(FormattedText([("bold", expression)]))
        print()
        print_formatted_text(HTML(result.explanation))
        print()

    original = result.script
    followed_up = False

    while True:
        if not clarify_mode:
            user_input = display_prompt(expression, show_go_back=False)
        else:
            user_input = display_clarity_prompt("")

        if user_input == EXIT:
            raise KeyboardInterrupt()
        elif user_input == TOGGLE_CLARIFY_MODE:
            clarify_mode = True
        elif user_input == GO_BACK:
            clarify_mode = False
        else:
            if not clarify_mode:
                expression = user_input
                break
            else:
                q = f"{q}\nsuggestion: {result.script}\n{user_input}"
                tpe = ThreadPoolExecutor(max_workers=2)
                task = tpe.submit(query, q=q)

                try:
                    loading = Simple("thinking...")
                    loading.step()
                    while not task.done():
                        time.sleep(0.1)
                        loading.step()
                    loading.clear()
                finally:
                    tpe.shutdown()

                results = task.result()
                if len(results) > 0:
                    result = results[0]
                    expression = result.script
                    print_formatted_text(FormattedText([("bold", expression)]))
                    if result.explanation is not None:
                        print_formatted_text(HTML(result.explanation))
                    followed_up = True
                clarify_mode = False
    r = copy(result)
    r.script = expression.strip()

    if not followed_up and r.script != original:
        # the user corrected the script
        db = corrections.get_db()
        vector = similarity.embedding(text=q)
        db.add(vector, corrections.QATuple(question=q, answer=original, corrected=r.script).to_dict())
        logging.debug("added correction to db")
        db.save(os.path.expanduser(settings.corrections_db_path))
        feedback({"corrected": True})

    return r


def do_query(question: str):
    db = corrections.get_db()

    question = question.strip()
    if question == "":
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

    embedding = similarity.embedding(text=question)
    similar = db.search(embedding, k=3, min_similarity=0.2)
    logging.debug("found %d similar questions", len(similar))
    for s, score in similar:
        qa = corrections.QATuple.from_dict(s)
        logging.debug(f"- {score:.2f}: {qa.question} -> {qa.corrected}")
    if len(similar) > 0:
        similar_qa = [corrections.QATuple.from_dict(s) for s, _ in similar]
        question = f"{question}\n\nTo answer take into account these previous responses that could be relevant:" + \
            "\n".join([f"\nQ:{qa.question}\nA:{qa.corrected}" for qa in similar_qa])

    tpe = ThreadPoolExecutor(max_workers=2)
    tasks = []
    if int(settings.history_context) > 0:
        try:
            past_cmds = get_shell().get_history(min(int(settings.history_context), 3))
            q = ""
            if len(past_cmds) > 0:
                q = "past commands:\n" + "\n".join(past_cmds) + "\n\n"
            q += question
            tasks.append(tpe.submit(query, q=q))
        except Exception as e:
            sys.stderr.write("encountered exception" + str(e) + "\n")
    tasks.append(tpe.submit(query, q=question))

    try:
        loading = Simple("thinking...")
        loading.step()
        while not all(task.done() for task in tasks):
            time.sleep(0.1)
            loading.step()
        loading.clear()
    finally:
        tpe.shutdown()

    results = [tr for task in tasks for tr in task.result()]
    results = deduplicate(results)
    if len(results) == 0:
        print("can't help you here :/")
        sys.exit(1)

    try:
        selected = run_confirm_loop(question, results[0])
    except KeyboardInterrupt:
        feedback({"cancelled": True})
        sys.exit(1)
    feedback({"run": True})
    try:
        rc = run(selected)
        feedback({
             "success": True,
             "rc": rc
        })
    except Exception as e:
        feedback({"error": str(e)})


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


def runner_mode(args):
    from local_runner.main import entry_point
    entry_point()


def entry_alias():
    import colorama
    colorama.init()
    # get the name of the calling script
    alias = os.path.basename(sys.argv[0])

    settings_store.load()
    parser = ArgumentParser(
        prog=alias,
        usage=f"{alias} [options] <question>\nexample: {alias} list running ec2 instances",
        description=f"{alias}: a command line assistant")
    parser.add_argument("--verbose", "-v", action="store_true", help="verbose output")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    parser.add_argument("--history-context", default=settings.history_context, type=int,
                        help="past commands to include in the query (default: %(default)s)")
    parser.add_argument("--explain", dest="explain", action="store_true", default=settings.request_explanation,
                        help="explain the commands and the parameters")
    parser.add_argument("--no-explain", dest="explain", action="store_false", default=settings.request_explanation,
                        help="no explanations = faster response")
    parser.add_argument("--mode", default=settings.model, choices=["fast", "accurate"],
                        help="fast or accurate (default: %(default)s)")
    parser.add_argument("question", nargs=REMAINDER, help="the question to ask")
    args = parser.parse_args()
    if args.version:
        from promptops.version import __version__
        print(__version__)
        sys.exit(0)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    query_mode(args)


def entry_main():
    import colorama
    colorama.init()

    settings_store.load()
    parser = ArgumentParser()
    parser.add_argument("--version", action="store_true", help="print version and exit")
    parser.add_argument("--verbose", "-v", action="store_true", help="verbose output")
    subparsers = parser.add_subparsers()
    parser_question = subparsers.add_parser("query", help="ask questions")
    parser_question.add_argument("--history-context", default=settings.history_context, type=int,
                                 help="number of past commands to include in the query (default: %(default)s)")
    parser_question.add_argument("--explain", dest="explain", action="store_true", default=settings.request_explanation,
                                 help="explain the commands and the parameters")
    parser_question.add_argument("--no-explain", dest="explain", action="store_false", default=settings.request_explanation,
                                 help="get faster response")
    parser_question.add_argument("--mode", default=settings.model, choices=["fast", "accurate"],
                                 help="fast or accurate (default: %(default)s)")
    parser_question.add_argument("question", nargs=REMAINDER, help="the question to ask")
    parser_question.set_defaults(func=query_mode)

    parser_runner = subparsers.add_parser("runner", help="run commands from slack")
    parser_runner.set_defaults(func=runner_mode)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        if args.version:
            from promptops import version
            print("promptops ", version.__version__)
            return

        parser.print_help()
        return

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    args.func(args)


if __name__ == "__main__":
    entry_main()
