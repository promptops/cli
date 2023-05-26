import time

from promptops.ui import selections
from promptops.query import query
import threading


def main():
    print("hello world!")
    print()
    results = [
        query.Result(
            script="QUEUE_URL=$(aws sqs get-queue-url --queue-name fleet-manager --query 'QueueUrl' --output text); aws sqs send-message --queue-url $QUEUE_URL --message-body 'Your message here'",
            # script="say cheese",
            origin="history",
        ),
        query.Result(
            script="python -m promptops.main query send message to sqs queue fleet-management",
            origin="history",
        ),
        query.Result(
            script="aws sqs list queues",
            origin="history",
        ),
    ]

    options = [query.pretty_result(r) for r in results]

    ui = selections.UI(
        options=options,
        is_loading=True,
    )

    def load():
        time.sleep(1)
        ui.add_options([], False)

    lt = threading.Thread(target=load, daemon=True)
    lt.start()

    index = ui.input()
    print(index)


if __name__ == "__main__":
    main()