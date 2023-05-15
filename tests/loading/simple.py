from promptops import loading
import time
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import FormattedText


def main():
    print_formatted_text(FormattedText([("bold", "hello")]))
    l = loading.Simple("thinking...")
    for i in range(10):
        l.step()
        time.sleep(0.1)
    l.clear()
    print_formatted_text(FormattedText([("", "bye")]))


if __name__ == "__main__":
    main()
