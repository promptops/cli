from promptops import history


def main():
    db = history.get_history_db()
    for item in db.objects:
        print(item)


if __name__ == "__main__":
    main()
