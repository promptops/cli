.PHONY: build install

build:
	python setup.py sdist

install:
	python setup.py install

clean:
	rm -f dist/*

package: clean
	python -m build .

publish: package
	python -m twine upload dist/*
