import subprocess
import sys
import threading
from typing import Tuple


def run_command(script, directory) -> Tuple[bool, str]:
    def printer(pipe, func):
        for line in iter(pipe.readline, b''):
            line_decoded = line.decode()
            sys.stdout.write(line_decoded)
            sys.stdout.flush()
            func(line)
        pipe.close()

    process = subprocess.Popen(
        script, shell=True, start_new_session=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=directory
    )
    stdout = []
    stderr = []

    thread_out = threading.Thread(target=printer, args=[process.stdout, lambda line: stdout.append(line.decode())])
    thread_err = threading.Thread(target=printer, args=[process.stderr, lambda line: stderr.append(line.decode())])

    thread_out.start()
    thread_err.start()
    thread_out.join()
    thread_err.join()

    sys.stdout.write("\n")
    sys.stdout.flush()

    process.wait()

    return process.returncode == 0, "".join(stderr)


