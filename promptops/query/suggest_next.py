import fnmatch
import logging
import os

import requests
from typing import List
from promptops import shells, settings, user, trace
import shlex
from thefuzz import fuzz


def similarity(cmd1, cmd2):
    try:
        tokens1 = shlex.split(cmd1)
        tokens2 = shlex.split(cmd2)
    except ValueError:
        tokens1 = cmd1.strip().split()
        tokens2 = cmd2.strip().split()
    if tokens1[0] != tokens2[0]:
        return 0
    # naive approach to weigh the tokens
    max_multiplier = 3
    m_tokens1 = []
    for i, token in enumerate(tokens1[1:max_multiplier]):
        m_tokens1.extend([token] * (max_multiplier - i))
    m_tokens1.extend(tokens1[max_multiplier:])
    m_tokens2 = []
    for i, token in enumerate(tokens2[1:max_multiplier]):
        m_tokens2.extend([token] * (max_multiplier - i))
    m_tokens2.extend(tokens2[max_multiplier:])
    return fuzz.ratio(m_tokens1, m_tokens2) / 100.0


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

    def close_enough_node(self, text, cutoff=0.7):
        def count_dicts(d):
            if not isinstance(d, dict):
                return 0
            return 1 + sum(count_dicts(v) for v in d.values())

        close = []
        for s2 in self.roots.keys():
            score = similarity(text, s2)
            if score > cutoff:
                if count_dicts(self.roots[s2]) > 1:
                    close.append(self.roots[s2])
        return close

    @staticmethod
    def closest_next(possible, text, cutoff=0.7):
        close = []
        for s2 in possible:
            score = similarity(text, s2)
            if score > cutoff:
                close.append((s2, score))
        if len(close) == 0:
            return None
        return max(close, key=lambda x: x[1])[0]

    def predict_next_close(self, command_sequence):
        if len(command_sequence) < 1 or command_sequence[0] not in self.roots:
            return None

        entry = command_sequence[0]
        entry_node = self.roots[entry]

        close = self.close_enough_node(entry)
        possibilities = {}

        def update(items):
            for item in items:
                possibilities[item] = possibilities.get(item, 0) + 1

        for node in close:
            if node == entry_node:
                continue

            for c, cmd in enumerate(command_sequence[1:]):
                if cmd in node:
                    node = node[cmd]['next']
                else:
                    possible_keys = [k for k in node.keys() if k != '$' and k != 'next']
                    possible_node_cmd = self.closest_next(possible_keys, command_sequence[c])
                    if possible_node_cmd:
                        node = node[possible_node_cmd]['next']

            update([k for k, v in node.items() if k != '$'])

        return [cmd for cmd, freq in sorted(possibilities.items(), key=lambda x: x[1], reverse=True)]

    def predict_next(self, command_sequence):
        if len(command_sequence) < 1 or command_sequence[0] not in self.roots:
            return None

        entry = command_sequence[0]
        node = self.roots[entry]

        for c, cmd in enumerate(command_sequence[1:]):
            if cmd in node:
                node = node[cmd]['next']
            else:
                continue

        next_cmds = [(k, v.get('$', 0)) for k, v in node.items() if k != '$']
        next_cmds.sort(key=lambda x: x[1], reverse=True)

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


def suggest_next_suffix(count: int = 2) -> List[dict]:
    context = shells.get_shell().get_recent_history(6)
    predictions = []

    for i in range(1, 6):
        prediction = suffix_tree.predict_next(context[-i:])
        if prediction:
            predictions = prediction + [p for p in predictions if p not in prediction]

    return [{'option': p, 'origin': 'history'} for p in predictions[:count]]


def suggest_next_suffix_near(count: int = 2) -> List[dict]:
    context = shells.get_shell().get_recent_history(6)
    predictions = []

    for i in range(1, 6):
        prediction = suffix_tree.predict_next_close(context[-i:])
        if prediction:
            predictions = prediction + [p for p in predictions if p not in prediction]

    return [{'option': p, 'origin': 'history'} for p in predictions[:count]]


def suggest_next_gpt() -> List[dict]:
    context = shells.get_shell().get_recent_history(4)
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

    return [{'option': p, 'origin': 'promptops'} for p in response.json().get("options")[:2]]


ORIGIN_SYMBOLS = {"history": "📖", "promptops": "✨", 'other': 'close-enough'}


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

