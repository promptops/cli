import fnmatch
import logging
import os
import threading
import random
from typing import List, Optional

import requests
from promptops.query.dtos import Result

from promptops.query.explanation import ReturningThread

from promptops.query import messages

from promptops import shells, settings, user, trace
from promptops.ui import selections, prompts


class SuffixTree:
    def __init__(self):
        self.roots = {}
        self.build_tree()

    def insert(self, command_sequence):
        if command_sequence[0] not in self.roots:
            self.roots[command_sequence[0]] = {}

        node = self.roots[command_sequence[0]]
        for cmd in command_sequence[1:]:
            if cmd not in node:
                node[cmd] = {'$': 0, 'next': {}}
            node = node[cmd]['next']
        node['$'] = node.get('$', 0) + 1

    def build_tree(self):
        lines = shells.get_shell().get_recent_history(1000)
        for i, line in enumerate(lines):
            root_cmd = line
            if root_cmd:
                self.insert(lines[i:i+3])

    def predict_next(self, command_sequence, embeddings=None):
        entry = command_sequence[0]
        if entry not in self.roots or len(command_sequence) < 1:
            return None

        node = self.roots[entry]

        for c, cmd in enumerate(command_sequence[1:]):
            if cmd in node:
                node = node[cmd]['next']
            # elif embeddings:
            #     embedding = embeddings[c + 1]
            #     possible_keys = node.keys()
            else:
                return None

        next_cmds = [(k, v['$']) for k, v in node.items() if k != '$']
        # sorting lowest to highest intentionally, we reverse later :)
        next_cmds.sort(key=lambda x: x[1])

        return [cmd for cmd, freq in next_cmds]


suffix_tree = SuffixTree()


def get_files():
    ignored_types = ['*.txt', '*.rtf', '*.xml', '*.json', '*.yaml', '*.csv', '*.jpg', '*.png',
                     '*.gif', '*.bmp', '*.tiff', '*.mp3', '*.wav', '*.mp4', '*.avi', '*.mov',
                     '*.zip', '*.tar', '*.gz', '*.rar', '*.log', '*.bak', '*.tmp', '*.swp',
                     '*.exe', '*.dll', '*.so', '*.bin', '*.o', '*.class', '*.pyc', '*.pyo',
                     '*.jar', '*.cfg', '*.ini', '*.properties']

    directory = os.getcwd()
    all_files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    files = [f for f in all_files if not any(fnmatch.fnmatch(f, pattern) for pattern in ignored_types)]
    return files


def suggest_next_suffix(count: int = 4) -> List[dict]:
    context = shells.get_shell().get_recent_history(6)
    context.reverse()

    predictions = []

    for i in range(1, 5):
        prediction = suffix_tree.predict_next(context[:i])
        if prediction:
            predictions.extend(prediction)
            predictions.reverse()

    return [{'option': p, 'origin': 'history'} for p in predictions][:count]

#
# def suggest_next_suffix_near(count: int = 2) -> List[dict]:
#     context = shells.get_shell().get_recent_history(6)
#     context.reverse()
#     predictions = []
#
#     response = requests.post(
#         settings.endpoint + "/embeddings",
#         json={
#             "trace_id": trace.trace_id,
#             "batch": context,
#         },
#         headers={
#             "user-agent": f"promptops-cli; user_id={user.user_id()}",
#         },
#     )
#     embeddings = response.json()['result']
#
#     for i in range(1, 5):
#         prediction = suffix_tree.predict_next(context[:i], embeddings)
#         if prediction:
#             predictions.extend(prediction)
#             predictions.reverse()
#
#     return [{'option': p, 'origin': 'history'} for p in predictions][:count]
#

def suggest_next_gpt() -> List[dict]:
    context = shells.get_shell().get_recent_history(6)
    context.reverse()
    files = get_files()

    response = requests.post(
        settings.endpoint + "/skills/predict",
        json={
            "trace_id": trace.trace_id,
            "previous_commands": context,
            "files": files
        },
        headers={
            "user-agent": f"promptops-cli; user_id={user.user_id()}",
        },
    )

    if response.status_code != 200 or not response.json().get("options"):
        logging.debug("failed to get suggestion for the next command", response.status_code, response.json())
        return []

    return [{'option': p, 'origin': 'promptops'} for p in response.json().get("options")]


ORIGIN_SYMBOLS = {"history": "📖", "promptops": "✨"}


def pretty_result(item):
    return f'{ORIGIN_SYMBOLS[item["origin"]]} {item["option"]}'


def deduplicate(results: list[dict]):
    results_set = set()
    final_results = []
    for result in results:
        if result.get('option') in results_set:
            continue
        results_set.add(result.get('option'))
        final_results.append(result)
    return final_results


def suggest_next() -> Optional[Result]:
    results = deduplicate(suggest_next_suffix())

    task = ReturningThread(
        suggest_next_gpt,
        daemon=True,
    )

    update_lock = threading.Lock()

    options = [pretty_result(r) for r in results]
    ui = selections.UI(options, True, loading_text=random.choice(messages.QUERY))

    def done_callback(thread: ReturningThread):
        try:
            with update_lock:
                results.extend(thread.result())
                if ui:
                    options = [pretty_result(r) for r in deduplicate(results)]
                    ui.reset_options(options, is_loading=False)
        except Exception as exc:
            logging.exception(exc)

    task.add_done_callback(done_callback)
    task.start()

    index = ui.input()
    selected = results[index]

    result = Result(
        script=selected['option'],
        origin=selected['origin'],
        explanation='inferred by history'
    )
    if selected == prompts.GO_BACK:
        return None
    elif selected == prompts.EXIT:
        raise KeyboardInterrupt()

    print()
    return result
