import threading
from unittest.mock import patch, MagicMock
import contextlib

history = [
    'cd ~/projects',
    'git clone https://github.com/user/repo.git',
    'cd repo',
    'ls',
    'vim README.md',
    'git add README.md',
    'git commit -m "Update README.md"',
    'git push origin main',
    'cd ..',
    'mkdir new_project',
    'cd new_project',
    'touch app.py',
    'vim app.py',
    'python3 app.py',
    'ls -a',
    'git init',
    'git add .',
    'git commit -m "Initial commit"',
    'cd ../repo',
    'git pull origin main',
    'cd ../new_project',
    'git remote add origin https://github.com/user/new_project.git',
    'git push -u origin main',
    'cd ~',
    'python3 -m venv env',
    'source env/bin/activate',
    'pip install numpy',
    'pip freeze > requirements.txt',
    'deactivate',
    'cd ~/projects/repo',
    'git checkout -b feature',
    'vim app.py',
    'git add app.py',
    'git commit -m "Add feature"',
    'git push origin feature',
    'cd ~/projects/new_project',
    'git pull origin main',
    'git merge feature',
    'git push origin main',
    'cd ~',
    'kubectl get pods',
    'kubectl describe pod my-pod',
    'kubectl delete pod my-pod',
    'kubectl apply -f my-deployment.yaml',
    'kubectl get deployments',
    'kubectl describe deployment my-deployment',
    'kubectl scale deployment my-deployment --replicas=3',
    'kubectl get pods',
    'kubectl exec -it my-pod -- /bin/bash',
    'exit',
    'docker build -t my-image .',
    'docker run -p 8000:8000 my-image',
    'docker ps',
    'docker stop my-container',
    'docker rm my-container',
    'docker rmi my-image',
    'aws s3 ls',
    'aws s3 cp my-file.txt s3://my-bucket',
    'aws s3 ls s3://my-bucket',
    'aws s3 rm s3://my-bucket/my-file.txt',
    'aws ec2 describe-instances',
    'aws ec2 start-instances --instance-ids i-1234567890abcdef0',
    'aws ec2 stop-instances --instance-ids i-1234567890abcdef0',
    'ssh -i "my-key.pem" ec2-user@ec2-198-51-100-1.compute-1.amazonaws.com',
    'exit',
    'cd ~/projects/repo',
    'git pull origin main',
    'git checkout -b bugfix',
    'vim app.py',
    'git add app.py',
    'git commit -m "Fix bug"',
    'git push origin bugfix',
    'cd ~/projects/new_project',
    'git pull origin main',
    'git merge bugfix',
    'git push origin main',
    'cd ~',
    'terraform init',
    'terraform plan',
    'terraform apply',
    'terraform destroy',
    'cd ~/projects/repo',
    'git checkout main',
    'git merge feature',
    'git merge bugfix',
    'git push origin main',
    'cd ~/projects/new_project',
    'git pull origin main',
    'git tag v1.0.0',
    'git push origin v1.0.0',
    'cd ~',
    'kubectl get services',
    'kubectl describe service my-service',
    'kubectl delete service my-service',
    'kubectl apply -f my-service.yaml',
]


_patch_lock = threading.Lock()


@contextlib.contextmanager
def patch_shell(recent_commands: list[str], history_replacement: list[str] = None):
    if history_replacement is None:
        history_replacement = history
    mock_shell = MagicMock()

    def get_recent_history(n: int):
        return (history_replacement + recent_commands)[-n:]

    mock_shell.get_recent_history.side_effect = get_recent_history
    mock_get_shell = MagicMock(return_value=mock_shell)
    with _patch_lock, patch('promptops.shells.get_shell', mock_get_shell):
        yield mock_shell


def test_git_commit_predict():
    with patch_shell(['git commit -m "i just made a few changes"']):
        from promptops.query import suggest_next
        suggest_next.suffix_tree = suggest_next.SuffixTree()
        near = suggest_next.suggest_next_suffix_near()
        print(near)

    assert len(near) == 2


def test_exact_predict():
    with patch_shell(['terraform init']):
        from promptops.query import suggest_next
        suggest_next.suffix_tree = suggest_next.SuffixTree()

        exact = suggest_next.suggest_next_suffix()
        print(exact)

    assert any([x.get('option') == 'terraform plan' for x in exact])


def test_another_one():
    with patch_shell(['kubectl get services']):
        from promptops.query import suggest_next
        suggest_next.suffix_tree = suggest_next.SuffixTree()

        exact = suggest_next.suggest_next_suffix(2)
        print(exact)

    assert any([x.get('option') == 'kubectl describe service my-service' for x in exact])


def test_simple():
    values = [
        "A", "B", "C",
        "X", "Y", "Z",
        "A", "B", "C",
        "1", "B", "D",
        "X", "Y", "Z",
    ]

    with patch_shell(["B"], values):
        from promptops.query import suggest_next
        suggest_next.suffix_tree = suggest_next.SuffixTree()

        options = suggest_next.suggest_next_suffix(2)
        assert [item["option"] for item in options] == ["C", "D"]

    with patch_shell(["1", "B"], values):
        from promptops.query import suggest_next
        suggest_next.suffix_tree = suggest_next.SuffixTree()

        options = suggest_next.suggest_next_suffix(2)
        assert [item["option"] for item in options] == ["D", "C"]

    with patch_shell(["A", "B"], values):
        from promptops.query import suggest_next
        suggest_next.suffix_tree = suggest_next.SuffixTree()

        options = suggest_next.suggest_next_suffix(2)
        assert [item["option"] for item in options] == ["C", "D"]
