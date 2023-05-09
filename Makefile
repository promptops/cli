.PHONY: build install

build:
	python setup.py sdist

install:
	python setup.py install
