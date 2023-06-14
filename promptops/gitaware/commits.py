import subprocess
import logging


def get_latest_commits(author=None, n=10):
    """Get the latest commits from the git repo"""
    try:
        if author is None:
            author = subprocess.check_output(['git', 'config', 'user.name'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        commits = subprocess.check_output(['git', 'log', '--pretty=format:%s', '--author=' + author, '-n', str(n)], stderr=subprocess.STDOUT).decode('utf-8').strip().split('\n')
        return commits
    except subprocess.CalledProcessError as e:
        logging.debug('return code: %d', e.returncode)
        return None


def get_staged_files():
    """Get the staged files from the git repo"""
    try:
        files = subprocess.check_output(["git", "status", "--porcelain"], stderr=subprocess.STDOUT).decode('utf-8').\
            split('\n')
        logging.debug('staged result: %s', files)
        files = [file[3:] for file in files if file.strip() and file[0] != ' ' and file[:2] != '??']
        return files
    except subprocess.CalledProcessError as e:
        logging.debug('return code: %d', e.returncode)
        return None


def get_unstaged_files():
    """Get the unstaged files from the git repo using the git status command"""
    try:
        files = subprocess.check_output(['git', 'status', '--porcelain'], stderr=subprocess.STDOUT).decode('utf-8')\
            .split('\n')
        logging.debug('unstaged result: %s', files)
        files = [file[3:] for file in files if file.strip() and file[1] != ' ']
        return files
    except subprocess.CalledProcessError as e:
        logging.debug('return code: %d', e.returncode)
        return None


def get_staged_changes():
    """Get the staged changes in the git repo"""
    try:
        changes = subprocess.check_output(['git', 'diff', '--staged'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        return changes
    except subprocess.CalledProcessError as e:
        raise ValueError(f"git diff failed with return code {e.returncode}")


def add_to_staging(files: list[str]):
    """Add files to the staging area"""

    rc = subprocess.call(["git", "add"] + files)
    if rc != 0:
        raise ValueError(f"git add failed with return code {rc}")
    return
