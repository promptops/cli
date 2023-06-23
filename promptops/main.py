"""
    PromptOps: Your CLI assistant. Ask questions, get shell commands.
    Copyright (C) 2023  CtrlStack, Inc

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
from argparse import ArgumentParser, REMAINDER
import sys
import os
import traceback

import logging

from promptops import settings
from promptops import settings_store
from promptops import version_check
from promptops import user

from promptops.feedback import feedback

ENDPOINT_ENV = "PROMPTOPS_ENDPOINT"


def runner_mode(args):
    from local_runner.main import entry_point

    feedback({"event": "runner_mode"})
    entry_point()


def check_if_installed():
    from promptops.shells import get_shell
    if not get_shell().is_installed():
        from prompt_toolkit import print_formatted_text
        from prompt_toolkit.formatted_text import HTML
        print()
        print_formatted_text(HTML("<ansired>Warning: um is not fully configured. To finish the installation, run:</ansired>"))
        print_formatted_text(HTML("<ansigreen>  eval \"$(um --install)\"</ansigreen>"))
        print()


def query_mode(args):
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings.model = args.mode
    settings.history_context = args.history_context
    settings.request_explanation = args.explain

    question = " ".join(args.question)
    try:
        if question.strip():
            feedback({"event": "query_mode"})
            from promptops import query
            query.do_query(question)
        else:
            feedback({"event": "dtt_mode"})
            from promptops.skills import dtt
            dtt.entry_point()
    except KeyboardInterrupt:
        pass
    if settings_store.is_changed():
        for _ in range(3):
            answer = input("save the current settings? [y/n]")
            if answer == "y":
                settings_store.save()
                break
            elif answer == "n":
                break
    check_if_installed()


def lookup_mode(args):
    from promptops.query.lookup import entry_point as lookup_entry_point

    lookup_entry_point(args)


def recipe_mode(args):
    from promptops.recipes.creation import recipe_entrypoint
    recipe_entrypoint(args)


def index_mode(args):
    from promptops.index.entry_point import entry_point as index_entry_point
    index_entry_point(args)


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

    import warnings
    warnings.filterwarnings("ignore", module='thefuzz')

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
    parser.add_argument("--shell-config", action="store_true", help="print configuration for your shell")
    parser.add_argument("--install", action="store_true", help="print install script")
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

    if args.shell_config:
        from promptops.shells import get_shell
        print(get_shell().get_config())
        sys.exit(0)
    if args.install:
        from promptops.shells import get_shell
        print(get_shell().install())
        sys.exit(0)

    if args.version:
        from promptops.version import __version__

        print(__version__)
        r = version_check.version_check()
        if not r.update_required:
            print("latest version:", r.latest_version)
        check_if_installed()
        sys.exit(0)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    version_check.version_check()

    if not registered or args.config:
        user.register()
        args.history_context = settings.history_context
    else:
        from promptops import history

        history.update_history()

    if args.question and len(args.question) > 0:
        if args.question[0] == 'workflow' or args.question[0] == 'recipe':
            return recipe_mode(args)
        elif args.question[0] == 'index':
            # index subcommand
            subparser = ArgumentParser(
                prog=f"{alias} index",
                usage=f"{alias} index [action]",
                description=f"{alias} index: manage the indexed data",
            )
            subparser.add_argument("action", choices=["list", "add", "remove", "test"], help="list or update the index")
            subparser.add_argument("--source", help="the source to add or remove")
            subparser.add_argument("--query", help="query to test with")
            sub_args = subparser.parse_args(args.question[1:])
            return index_mode(sub_args)
    query_mode(args)


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
    parser_question.add_argument("--shell-config", action="store_true", help="print configuration for your shell")
    parser_question.add_argument("--install", action="store_true", help="print install script")
    parser_question.add_argument("question", nargs=REMAINDER, help="the question to ask")
    parser_question.set_defaults(func=query_mode)

    parser_runner = subparsers.add_parser("runner", help="run commands from slack")
    parser_runner.set_defaults(func=runner_mode)

    parser_workflow = subparsers.add_parser("recipe", help="run a complex or multi-stepped script")
    parser_workflow.add_argument("question", nargs=REMAINDER, help="the question to generate scripts for")
    parser_workflow.set_defaults(func=recipe_mode)

    parser_index = subparsers.add_parser("index", help="manage the indexed data")
    parser_index.add_argument("action", choices=["list", "add", "remove", "test"], help="list or update the index")
    parser_index.add_argument("--source", help="the source to add or remove")
    parser_index.add_argument("--query", help="query to test with")
    parser_index.set_defaults(func=index_mode)

    parser_lookup = subparsers.add_parser("lookup", help="extended reverse search, use --config to configure in your shell")
    parser_lookup.add_argument("--config", action="store_true", help="print configuration for your shell")
    parser_lookup.add_argument("command", nargs=REMAINDER, help="the command to lookup")
    parser_lookup.set_defaults(func=lookup_mode)

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
            args.history_context = settings.history_context
            sys.exit(0)

        parser.print_help()
        return

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    if getattr(args, "func") == lookup_mode:
        if not args.verbose:
            logging.basicConfig(level=logging.ERROR, format="%(message)s", force=True)
        # shortcut for lookup
        args.func(args)
        return

    version_check.version_check()
    if not registered:
        user.register()
        args.history_context = settings.history_context
    else:
        from promptops import history

        history.update_history()
    args.func(args)


if __name__ == "__main__":
    entry_main()
