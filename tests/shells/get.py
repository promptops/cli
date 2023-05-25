from promptops.shells import get_shell


def main():
    shell = get_shell()
    print(f"shell: {shell.__class__.__name__}")

    print("---recent---")
    recent = shell.get_recent_history(look_back=100)
    for cmd in recent:
        print("$", cmd)

    print("---full---")
    full = shell.get_full_history()
    for cmd in full[-10:]:
        print("$", cmd)


if __name__ == "__main__":
    main()
