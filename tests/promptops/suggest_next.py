import unittest
from unittest.mock import Mock, patch, MagicMock

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
    'kubectl get services'
]


class TestMyFunction(unittest.TestCase):

    def setUp(self):
        self.mock_shell = MagicMock()
        self.mock_get_shell = MagicMock(return_value=self.mock_shell)


    def setValue(self, v):
        def side_effect(arg):
            if arg == 1000:
                return history + [v]
            elif arg == 6:
                return history + [v]
            else:
                return history

        self.mock_shell.get_recent_history.side_effect = side_effect


    def test_git_commit_predict(self):
        self.setValue('git commit -m "i just made a few changes"')

        with patch('promptops.shells.get_shell', self.mock_get_shell):
            from promptops.query.suggest_next import suggest_next_suffix_near

            near = suggest_next_suffix_near()
            print(near)

        self.assertTrue(len(near) == 2)


    def test_exact_predict(self):
        self.setValue('terraform init')

        with patch('promptops.shells.get_shell', self.mock_get_shell):
            from promptops.query.suggest_next import suggest_next_suffix

            exact = suggest_next_suffix()
            print(exact)

        self.assertTrue(any([x.get('option') == 'terraform plan' for x in exact]))


    def another_one(self):
        self.setValue('kubectl get services')

        with patch('promptops.shells.get_shell', self.mock_get_shell):
            from promptops.query.suggest_next import suggest_next_suffix

            exact = suggest_next_suffix(2)
            print(exact)

        self.assertTrue(any([x.get('option') == 'kubectl describe service my-service' for x in exact]))



if __name__ == "__main__":
    unittest.main()