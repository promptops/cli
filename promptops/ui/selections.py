import sys
import time
import threading
import os
import re
import typing
from promptops.loading.simple import loader
from prompt_toolkit.formatted_text import to_plain_text, ANSI
import wcwidth
import colorama


FOOTER_SECTIONS = {
    "select": f"{colorama.Style.BRIGHT}[↑/↓]{colorama.Style.RESET_ALL} select",
    "confirm": f"{colorama.Style.BRIGHT}[enter]{colorama.Style.RESET_ALL} confirm",
    "cancel": f"{colorama.Style.BRIGHT}[ctrl+c]{colorama.Style.RESET_ALL} cancel",
    "copy": f"{colorama.Style.BRIGHT}[c]{colorama.Style.RESET_ALL} copy",
}


class UI(object):
    def __init__(
        self,
        options: list[str],
        is_loading: bool,
        cursor="➜︎",
        show_timer=False,
        loading_text="getting you the best results ...",
        footer=" ".join([FOOTER_SECTIONS["select"], FOOTER_SECTIONS["confirm"], FOOTER_SECTIONS["cancel"]]),
        actions: dict[str, typing.Callable[[str, "UI"], None]] = None,
        header=""
    ):
        self._selected = 0
        self._options = options
        self._is_loading = is_loading
        self._start = time.time()
        self._cursor = cursor
        self._footer = footer
        self._header = header
        self._loading_line_index = None
        self._option_indexes = []
        self._thread = threading.Thread(target=self._loading_animation, daemon=True)
        self._show_timer = show_timer
        self._spinner = loader(loading_text)
        self._lock = threading.Lock()
        self._is_active = True
        self._actions = actions or {}

        self._lines_written = 0
        self._raw_mode = False
        self._old_stdin_attrs = None
        self._offset = 0
        self._estimated_lines = []
        self._usable_lines = 0
        self.render()
        self._thread.start()

    def render(self):
        with self._lock:
            if self._raw_mode:
                import termios
                fd = sys.stdin.fileno()
                termios.tcsetattr(fd, termios.TCSADRAIN, self._old_stdin_attrs)

            # clean all the lines that were written
            sys.stdout.write("\x1b[2K")
            for _ in range(self._lines_written):
                sys.stdout.write("\x1b[1A\x1b[2K")
            sys.stdout.write("\r")

            size = os.get_terminal_size()
            width = size.columns
            height = size.lines
            extra_lines = 0
            if self._header:
                extra_lines += 2
            if self._is_loading:
                extra_lines += 1
            if self._footer:
                extra_lines += 2
            self._usable_lines = height - extra_lines
            self._option_indexes = []

            current_line = 0
            if self._header:
                sys.stdout.write(f"{self._header}\n\n")
                current_line += 2
            option_lines = 0
            for i, option in enumerate(self._options):
                self._option_indexes.append(current_line)
                if i == self._selected:
                    text = f" {self._cursor} {self._get_formatted_text(option, True)}"
                else:
                    text = f"   {self._get_formatted_text(option, False)}"
                estimated_lines = 0
                for line in to_plain_text(ANSI(text)).split("\n"):
                    text_width = wcwidth.wcswidth(line)
                    estimated_lines += 1  # we always write at least one line
                    estimated_lines += text_width // width
                self._estimated_lines.append(estimated_lines)
                if i < self._offset:
                    continue
                option_lines += estimated_lines
                if option_lines <= self._usable_lines:
                    sys.stdout.write(f"{text}\n")
                    current_line += estimated_lines

            if self._is_loading:
                self._loading_line_index = current_line
                if self._show_timer:
                    sys.stdout.write(f"   {self._spinner(advance=False)} {(time.time() - self._start):.2f}s\n")
                else:
                    sys.stdout.write(f"   {self._spinner(advance=False)}\n")
                current_line += 1

            if self._footer:
                sys.stdout.write(f"\n{self._footer}")
                current_line += 1

            self._lines_written = current_line

            sys.stdout.flush()
            if self._raw_mode:
                import tty
                fd = sys.stdin.fileno()
                tty.setraw(fd)

    def _loading_animation(self):
        while True:
            with self._lock:
                if self._is_loading:
                    sys.stdout.write("\x1b7")
                    sys.stdout.write(f"\x1b[{self._lines_written - self._loading_line_index}A")
                    sys.stdout.write("\x1b[2K\r")
                    if self._show_timer:
                        sys.stdout.write(f"   {self._spinner()} {(time.time() - self._start):.2f}s\n")
                    else:
                        sys.stdout.write(f"   {self._spinner()}\n")
                    sys.stdout.write("\x1b8")
                    sys.stdout.flush()

            time.sleep(0.1)

    def select(self, index):
        if index == self._selected:
            return
        if len(self._options) == 0:
            return
        if index < self._offset:
            self._offset = index
            self._selected = index
            self.render()
            return
        elif index > self._selected:
            # check if we need to scroll down
            new_offset = self._offset
            while sum(self._estimated_lines[new_offset: index + 1]) > self._usable_lines:
                new_offset += 1
            if self._offset != new_offset:
                self._offset = new_offset
                self._selected = index
                self.render()
                return
        with self._lock:
            sys.stdout.write("\x1b7")
            sys.stdout.write(f"\x1b[{self._lines_written - self._option_indexes[index]}A")
            sys.stdout.write(f"\r {self._cursor} {self._get_formatted_text(self._options[index], True)}")
            sys.stdout.write("\x1b8")
            sys.stdout.write("\x1b7")
            sys.stdout.write(f"\x1b[{self._lines_written - self._option_indexes[self._selected]}A")
            sys.stdout.write(f"\r   {self._get_formatted_text(self._options[self._selected], False)}")
            sys.stdout.write(f"\x1b[{self._lines_written}B")
            sys.stdout.write("\x1b8")
            sys.stdout.flush()
            self._selected = index

    @property
    def selected(self):
        return self._selected

    @property
    def options(self):
        return self._options

    @property
    def is_loading(self):
        return self._is_loading

    @staticmethod
    def _get_formatted_text(option: str, selected: bool):
        opt = "\n".join(
                [(colorama.Fore.LIGHTYELLOW_EX if re.match("^. *#.*$", line) else colorama.Fore.LIGHTWHITE_EX) + line
                 for line in option.split("\n")]
        )
        return f"{colorama.Style.BRIGHT if selected else ''}{opt}{colorama.Style.RESET_ALL}".replace("\n", "\n      ")

    def add_options(self, options, is_loading=False):
        if not self._is_active:
            return
        self._options.extend(options)
        self._is_loading = is_loading
        self.render()

    def reset_options(self, options, is_loading=False):
        if not self._is_active:
            return
        self._options = options
        if self._selected >= len(self._options):
            self._selected = len(self._options) - 1
        self._is_loading = is_loading
        self.render()

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

    def input(self):
        while True:
            key = self.getch()
            if key == "\x03":
                if self._footer:
                    sys.stdout.write("\r\x1b[K")
                raise KeyboardInterrupt()
            elif key == "\x1b":
                next_ch = self.getch()
                if next_ch == "[":
                    last_ch = self.getch()
                    if last_ch == "A":
                        index = max(0, self._selected - 1)
                        self.select(index)
                    elif last_ch == "B":
                        index = min(len(self._options) - 1, self._selected + 1)
                        self.select(index)
            elif key in ["\r", "\n"]:
                self._is_active = False
                self._is_loading = False
                self._footer = None
                self.render()
                return self._selected
            elif key in self._actions:
                self._actions[key](key, self)

    @property
    def is_active(self):
        return self._is_active
