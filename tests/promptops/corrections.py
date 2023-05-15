from promptops import corrections


def main():
    db = corrections.get_db()
    for item in db.objects:
        print(item)


if __name__ == "__main__":
    main()
