from promptops.gitaware.commits import get_latest_commits


def list_commits():
    commits = get_latest_commits(n=3)
    for i, commit in enumerate(commits, start=1):
        print(i, commit)
        print("EOC")


if __name__ == "__main__":
    list_commits()
