checkfiles = tortoise/ examples/ setup.py
mypy_flags = --ignore-missing-imports --allow-untyped-decorators

help:
	@echo  "Tortoise-ORM development makefile"
	@echo
	@echo  "usage: make <target>"
	@echo  "Targets:"
	@echo  "    up          Updates dev/test dependencies"
	@echo  "    deps        Ensure dev/test dependencies are installed"
	@echo  "    check	Checks that build is sane"
	@echo  "    lint	Reports all linter violations"
	@echo  "    test	Runs all tests"
	@echo  "    docs 	Builds the documentation"

up:
	pip-compile -o requirements-dev.txt requirements-dev.in -U

deps:
	@pip install -q pip-tools
	@pip-sync requirements-dev.txt

check: deps
	flake8 $(checkfiles)
	mypy $(mypy_flags) $(checkfiles)
	pylint -E $(checkfiles)
	python setup.py check -mrs

lint: deps
	-flake8 $(checkfiles)
	-mypy $(mypy_flags) $(checkfiles)
	-pylint $(checkfiles)
	-python setup.py check -mrs

testtox:
	@echo "Not Implemented"

test: deps testtox

travis: check test bench

docs: deps
	python setup.py build_sphinx -E
