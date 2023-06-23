import sys
import threading
import queue

from promptops.feedback import feedback

from promptops.similarity import embedding
from promptops.history import get_history_db
from promptops.corrections import get_db
from thefuzz import process, fuzz
from promptops.shells import get_shell_name


class App:
    def getch(self):
        if sys.platform == "win32":
            import msvcrt

            return msvcrt.getwch()
        else:
            import tty
            import termios

            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            self._old_stdin_attrs = old
            try:
                tty.setraw(fd)
                self._raw_mode = True
                return sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
                self._raw_mode = False

    def __init__(self, max_items=5):
        self.text = ""
        self.queue = queue.Queue()
        self.options = []
        self.lines = 0
        self._lock = threading.RLock()
        self._raw_mode = False
        self._old_stdin_attrs = None
        self._max_items = max_items
        self._selected = 0
        self._loading = False

        self._hist_db = get_history_db()
        self._corrections_db = get_db()

        self.loader_thread = threading.Thread(target=self.loader, daemon=True)
        self.loader_thread.start()

    def run(self):
        sys.stderr.write("> ")
        sys.stderr.flush()

        while True:
            ch = self.getch()
            with self._lock:
                if ch in ['\n', '\r']:
                    break
                elif ch in ["\x08", "\x7f"]:
                    if len(self.text) <= 0:
                        continue
                    sys.stderr.write("\x1b[D\x1b[0K")
                    sys.stderr.flush()
                    self.text = self.text[:-1]
                    self.queue.put(self.text)
                elif ch == "\x03":
                    raise KeyboardInterrupt()
                elif ch == "\x1b":
                    next_ch = self.getch()
                    if next_ch == "[" or next_ch == "O":
                        last_ch = self.getch()
                        if last_ch == "A":
                            index = max(0, self._selected - 1)
                            self.select(index)
                        elif last_ch == "B":
                            index = min(len(self.options) - 1, self._selected + 1)
                            self.select(index)
                else:
                    self.text += ch
                    sys.stderr.write(ch)
                    sys.stderr.flush()
                    self.queue.put(self.text)
        return self.options[self._selected] if self.options else None

    def loader(self):
        while True:
            item = self.queue.get(block=True)
            if item is None:
                break
            while True:
                try:
                    item = self.queue.get(timeout=0.5)
                except queue.Empty:
                    break

            if len(item) < 2:
                self.options = []
                self.render()
                continue
            # TODO: include text matches
            matches = process.extract(
                item,
                [obj.get("cmd") if isinstance(obj, dict) else obj for obj in self._hist_db.objects],
                limit=self._max_items,
                scorer=fuzz.token_sort_ratio,
            )
            corrected_matches = process.extract(
                item,
                self._corrections_db.objects,
                limit=self._max_items,
                processor=lambda x: x["question"] if isinstance(x, dict) else x,
            )
            matches.extend([(r["corrected"], score) for r, score in corrected_matches])
            matches = [(match, score / 100) for match, score in matches]
            matches = sorted(matches, key=lambda x: x[1], reverse=True)
            # dedupe
            added = set()
            for i, (match, score) in enumerate(matches):
                if match in added:
                    continue
                added.add(match)
                matches[len(added) - 1] = (match, score)
            matches = matches[:len(added)]
            self.options = [match for match, _ in matches[:self._max_items // 2]]
            self._selected = 0
            self._loading = True
            self.render()
            try:
                value = embedding(text=item)

                hist_items = self._hist_db.search(value, min_similarity=0.1, k=self._max_items)
                hist_items = [(obj, score) for obj, score in hist_items if not isinstance(obj, dict) or not obj.get("ignore", False)]
                hist_items = [(r if isinstance(r, str) else r["cmd"], score) for r, score in hist_items]
                corr_items = self._corrections_db.search(value, min_similarity=0.1, k=self._max_items)
                corr_items = [(r["corrected"], score) for r, score in corr_items]

                sem_matches = hist_items + corr_items
                sem_matches = sorted(sem_matches, key=lambda x: x[1], reverse=True)

                # IMPORTANT! don't sort, so we do not reshuffle the results while the user is selecting
                matches.extend(sem_matches)
                added = set()
                for i, (match, score) in enumerate(matches):
                    if match in added:
                        continue
                    added.add(match)
                    matches[len(added) - 1] = (match, score)
                matches = matches[:len(added)]

                self.options = [match for match, _ in matches[:self._max_items]]
                self.render()
            except Exception as e:
                self.options = [str(e)]
                self._loading = False
                self.render()

    def render(self):
        with self._lock:
            if self._raw_mode:
                import termios
                fd = sys.stdin.fileno()
                termios.tcsetattr(fd, termios.TCSADRAIN, self._old_stdin_attrs)
            # save the current cursor position
            sys.stderr.write("\x1b7")
            sys.stderr.write("\x1b[0J")
            self.lines = 0
            for index, option in enumerate(self.options):
                text = option
                text = option.split("\n")[0]
                if index == self._selected:
                    text = f"\x1b[7m{text}\x1b[0m"
                sys.stderr.write(f"\n\r{text}")
                self.lines += 1

            if self._loading:
                sys.stderr.write(f"\n\r\x1b[2mloading...\x1b[0m")
                self.lines += 1

            # restore the cursor position
            sys.stderr.write(f"\x1b[{self.lines + 1}A")
            sys.stderr.write("\x1b8")
            sys.stderr.flush()
            if self._raw_mode:
                import tty
                fd = sys.stdin.fileno()
                tty.setraw(fd)

    def select(self, index):
        if index == self._selected:
            return
        if len(self.options) == 0:
            return
        with self._lock:
            sys.stderr.write("\x1b7")
            sys.stderr.write(f"\x1b[{index + 1}B")
            sys.stderr.write(f"\r\x1b[7m{self.options[index]}\x1b[0m")
            sys.stderr.write("\x1b8")
            sys.stderr.write("\x1b7")
            sys.stderr.write(f"\x1b[{self._selected + 1}B")
            sys.stderr.write(f"\r{self.options[self._selected]}")
            sys.stderr.write(f"\x1b[{self.lines}A")
            sys.stderr.write("\x1b8")
            sys.stderr.flush()
            self._selected = index


CONFIG_SCRIPTS = {
    "zsh": """
function extended-search () {
    local output=$(promptops lookup </dev/tty)
    zle kill-whole-line
    LBUFFER="${output}"
    zle redisplay
}
zle -N extended-search
bindkey "^E" extended-search
""",
    "bash": """
function extended-search () {
    local output=$(promptops lookup </dev/tty)
    READLINE_LINE="${output}"
    READLINE_POINT=${#output}
}
bind -x '"\\C-e": extended-search'
""",
    "fish": """
function extended-search
    set -l output (promptops lookup </dev/tty)
    commandline -r $output
end
bind \\ce extended-search
""",
}


def entry_point(args):
    if args.config:
        shell_name = get_shell_name()
        if shell_name != "zsh":
            sys.stderr.write("Only zsh is supported for now.")
            sys.exit(1)
        if shell_name in CONFIG_SCRIPTS:
            sys.stdout.write(CONFIG_SCRIPTS[shell_name])
            sys.stdout.flush()
            return
        sys.exit(1)

    feedback({"event": "lookup_mode"})
    # give us some space
    max_results = 10
    sys.stderr.write("\n"*(max_results + 1))
    sys.stderr.write(f"\x1b[{max_results}A")

    try:
        text = App(max_items=max_results).run()
    except KeyboardInterrupt:
        feedback({"event": "lookup-cancel"})
        sys.exit(1)
    if text is None:
        sys.exit(1)
    sys.stdout.write(text)
    sys.stdout.flush()
