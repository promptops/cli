import subprocess
import logging


def git_root():
    try:
        return subprocess.check_output(["git", "rev-parse", "--show-toplevel"], stderr=subprocess.STDOUT).decode("utf-8").strip()
    except subprocess.CalledProcessError as e:
        logging.debug("return code: %d", e.returncode)
        return None


def is_ignored(path):
    try:
        subprocess.check_output(["git", "check-ignore", path], stderr=subprocess.STDOUT)
        return True
    except subprocess.CalledProcessError as e:
        logging.debug("%s return code: %d", path, e.returncode)
        if e.returncode == 1:
            return False
        else:
            return True
