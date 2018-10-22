checkfiles = tortoise/ examples/
mypy_flags = --warn-unused-configs --warn-redundant-casts --ignore-missing-imports --allow-untyped-decorators

help:
	@echo  "Tortoise ORM development makefile"
	@echo
	@echo  "usage: make <target>"
	@echo  "Targets:"
	@echo  "    up          Updates dev/test dependencies"
	@echo  "    deps        Ensure dev/test dependencies are installed"
	@echo  "    check	Checks that build is sane"
	@echo  "    lint	Reports all linter violations"
	@echo  "    test	Runs all tests"
	@echo  "    docs 	Builds the documentation"
	@echo  "    style       Auto-formats the code"

up:
	pip-compile -o requirements-dev.txt requirements-dev.in -U

deps:
	@pip install -q pip-tools
	@pip-sync requirements-dev.txt

check: deps
	flake8 $(checkfiles)
	mypy $(mypy_flags) $(checkfiles)
	pylint -E $(checkfiles)
	bandit -r $(checkfiles)
	python setup.py check -mrs

lint: deps
	-flake8 $(checkfiles)
	-mypy $(mypy_flags) $(checkfiles)
	-pylint $(checkfiles)
	-bandit -r $(checkfiles)
	-python setup.py check -mrs

test: deps
	coverage erase
	coverage run -p --concurrency=multiprocessing `which green`
	coverage combine
	coverage report

testall: deps
	coverage erase
	TORTOISE_TEST_DB=sqlite://:memory: coverage run -p --concurrency=multiprocessing `which green`
	TORTOISE_TEST_DB=postgres://postgres:@127.0.0.1:5432/test_\{\} coverage run -p --concurrency=multiprocessing `which green`
	TORTOISE_TEST_DB="mysql://root:@127.0.0.1:3306/test_\{\}" coverage run -p --concurrency=multiprocessing `which green`
	coverage combine
	coverage report

ci: check test

docs: deps
	python setup.py build_sphinx -E

style: deps
	@#yapf -i -r $(checkfiles)
	isort -rc $(checkfiles)
