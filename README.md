`um` is a GPT-powered CLI assistant. Ask questions in plain English, get the perfect shell command.

<img src="https://github.com/promptops/cli/raw/main/media/default.png" />

# Features

- find the right command without leaving the terminal
- `um` can index your history to find commands you've run before
- `um` instantly learns from your corrections
- `um workflow` can help you provision infrastructure
- simple interface to clarify your question or provide more context

# Installation

## Linux - Ubuntu
```shell
curl -fsSL -o ubuntu-installer.sh https://raw.githubusercontent.com/promptops/cli/main/ubuntu-installer.sh
chmod 700 ubuntu-installer.sh
./ubuntu-installer.sh
```

## MacOS - Homebrew

```shell
brew install promptops/promptops/promptops-cli
```

## pip 

Make sure you have python 3.10 or more recent
[python.org downloads](https://www.python.org/downloads/)

```shell
pip3 install promptops
```

# Usage

## um

```shell
um <question>
```

```shell
um workflow <multi-stepped-prompt>
```

## local runner

```shell
promptops runner
```

# Examples

```shell
um list contents of tar file
um upload file to s3
```

## More screenshots

Semantic search in history

<img src="https://github.com/promptops/cli/raw/main/media/semantic-search.png" />

Provide more context flow

<img src="https://github.com/promptops/cli/raw/main/media/clarify.png" />

# Development setup

create virtual env

```shell
python3.10 -m venv ./venv
. ./venv/bin/activate
```

install dependencies

```shell
pip install -r requirements.txt
```

install the cli

```shell
make install
```

test with

```shell
um get pods
```
