# Installation

## using pip (preferred)
Make sure you have python 3.10 or more recent
```shell
pip3 install git+https://github.com/promptops/cli.git
```

## using homebrew (MacOS only)
```shell
brew install promptops/promptops/promptops-cli
```


# Usage

## um

```shell
um <question>
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


# Development setup

create virtual env

```shell
python3 -m venv ./venv
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
