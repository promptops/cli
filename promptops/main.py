from argparse import ArgumentParser, REMAINDER
import sys
import os
import traceback

import logging

from promptops import settings
from promptops import settings_store
from promptops import version_check
from promptops import query
from promptops import user
from promptops.recipes.creation import workflow_entrypoint

ENDPOINT_ENV = "PROMPTOPS_ENDPOINT"


def runner_mode(args):
    from feedback import feedback

    feedback(
        {
            "event": "runner_mode",
        }
    )

    from local_runner.main import entry_point

    entry_point()


def handle_exception(prev_handler):
    def inner(exc_type, exc_value, exc_traceback):
        sys.stderr.flush()
        if prev_handler:
            prev_handler(exc_type, exc_value, exc_traceback)
        error_message = traceback.format_exception(exc_type, exc_value, exc_traceback)
        from promptops.feedback import feedback

        feedback(
            {
                "event": "unhandled_exception",
                "error": error_message,
            }
        )

    return inner


def entry_alias():
    # Set the global exception handler
    sys.excepthook = handle_exception(sys.excepthook)

    import colorama

    colorama.init()
    # get the name of the calling script
    alias = os.path.basename(sys.argv[0])

    settings_store.load()
    if endpoint := os.environ.get(ENDPOINT_ENV):
        settings.endpoint = endpoint
    parser = ArgumentParser(
        prog=alias,
        usage=f"{alias} [options] <question>\nexample: {alias} list running ec2 instances",
        description=f"{alias}: a command line assistant",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="verbose output")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    parser.add_argument("--config", action="store_true", help="reconfigure")
    parser.add_argument(
        "--history-context",
        default=settings.history_context,
        type=int,
        help="past commands to include in the query (default: %(default)s)",
    )
    parser.add_argument(
        "--explain",
        dest="explain",
        action="store_true",
        default=settings.request_explanation,
        help="explain the commands and the parameters",
    )
    parser.add_argument(
        "--no-explain",
        dest="explain",
        action="store_false",
        default=settings.request_explanation,
        help="no explanations = faster response",
    )
    parser.add_argument(
        "--mode", default=settings.model, choices=["fast", "accurate"], help="fast or accurate (default: %(default)s)"
    )
    parser.add_argument("question", nargs=REMAINDER, help="the question to ask")
    registered = user.has_registered()
    args = parser.parse_args()
    if args.version:
        from promptops.version import __version__

        print(__version__)
        r = version_check.version_check()
        if not r.update_required:
            print("latest version:", r.latest_version)
        sys.exit(0)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    version_check.version_check()
    if not registered or args.config:
        user.register()
    else:
        from promptops import history

        history.update_history()
    query.query_mode(args)


def entry_main():
    # Set the global exception handler
    sys.excepthook = handle_exception(sys.excepthook)

    import colorama

    colorama.init()

    settings_store.load()
    if endpoint := os.environ.get(ENDPOINT_ENV):
        settings.endpoint = endpoint
    parser = ArgumentParser()
    parser.add_argument("--version", action="store_true", help="print version and exit")
    parser.add_argument("--verbose", "-v", action="store_true", help="verbose output")
    parser.add_argument("--config", action="store_true", help="reconfigure")
    subparsers = parser.add_subparsers()
    parser_question = subparsers.add_parser("query", help="ask questions")
    parser_question.add_argument(
        "--history-context",
        default=settings.history_context,
        type=int,
        help="number of past commands to include in the query (default: %(default)s)",
    )
    parser_question.add_argument(
        "--explain",
        dest="explain",
        action="store_true",
        default=settings.request_explanation,
        help="explain the commands and the parameters",
    )
    parser_question.add_argument(
        "--no-explain",
        dest="explain",
        action="store_false",
        default=settings.request_explanation,
        help="get faster response",
    )
    parser_question.add_argument(
        "--mode", default=settings.model, choices=["fast", "accurate"], help="fast or accurate (default: %(default)s)"
    )
    parser_question.add_argument("question", nargs=REMAINDER, help="the question to ask")
    parser_question.set_defaults(func=query.query_mode)

    parser_runner = subparsers.add_parser("runner", help="run commands from slack")
    parser_runner.set_defaults(func=runner_mode)

    parser_workflow = subparsers.add_parser("workflow", help="run a complex or multi-stepped script")
    parser_workflow.add_argument("question", nargs=REMAINDER, help="the question to generate scripts for")
    parser_workflow.set_defaults(func=workflow_entrypoint)

    args = parser.parse_args()

    registered = user.has_registered()

    if not hasattr(args, "func"):
        if args.version:
            from promptops.version import __version__

            print(__version__)

            r = version_check.version_check()
            if not r.update_required:
                print("latest version:", r.latest_version)
            sys.exit(0)
        if args.config:
            user.register()
            sys.exit(0)

        parser.print_help()
        return

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    version_check.version_check()
    if not registered:
        user.register()
    else:
        from promptops import history

        history.update_history()
    args.func(args)


if __name__ == "__main__":
    entry_main()
