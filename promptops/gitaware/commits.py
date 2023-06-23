from dataclasses import dataclass
import subprocess
import logging


def get_latest_commits(*, author=None, n=5):
    """Get the latest commits from the git repo"""
    try:
        if author is None:
            author = subprocess.check_output(['git', 'config', 'user.name'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        separator = '|||'
        commit_lines = subprocess.check_output(['git', 'log', '--pretty=format:%B%n'+separator, '--author=' + author, '-n', str(n)], stderr=subprocess.STDOUT).decode('utf-8').strip().split('\n')
        commits = []
        buffer = ""
        for line in commit_lines:
            if line == separator:
                buffer = buffer.strip()
                if buffer:
                    commits.append(buffer)
                buffer = ""
            else:
                buffer += line + '\n'
        buffer = buffer.strip()
        if buffer:
            commits.append(buffer)
        return commits
    except subprocess.CalledProcessError as e:
        logging.debug('return code: %d', e.returncode)
        return None


@dataclass
class Change:
    file: str
    modifier: str

    def modifier_desc(self):
        if self.modifier == 'A':
            return 'added'
        elif self.modifier == 'M':
            return 'modified'
        elif self.modifier == 'D':
            return 'deleted'
        elif self.modifier == 'R':
            return 'renamed'
        elif self.modifier == 'C':
            return 'copied'
        elif self.modifier == 'U':
            return 'updated'
        elif self.modifier == '?':
            return 'untracked'
        else:
            return 'Unknown'


def get_staged_files() -> list[Change]:
    """Get the staged files from the git repo"""
    try:
        files = subprocess.check_output(["git", "status", "--porcelain"], stderr=subprocess.STDOUT).decode('utf-8').\
            split('\n')
        logging.debug('staged result: %s', files)
        changes = [Change(file[3:], modifier=file[0]) for file in files if file.strip() and file[0] != ' ' and file[:2] != '??']
        return changes
    except subprocess.CalledProcessError as e:
        logging.debug('return code: %d', e.returncode)
        return None


def get_unstaged_files() -> list[Change]:
    """Get the unstaged files from the git repo using the git status command"""
    try:
        files = subprocess.check_output(['git', 'status', '--porcelain'], stderr=subprocess.STDOUT).decode('utf-8')\
            .split('\n')
        logging.debug('unstaged result: %s', files)
        changes = [Change(file[3:], modifier=file[1]) for file in files if file.strip() and file[1] != ' ']
        return changes
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
