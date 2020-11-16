checkfiles = tortoise/ examples/ tests/ conftest.py
black_opts = -l 100 -t py37
py_warn = PYTHONDEVMODE=1

help:
	@echo  "Tortoise ORM development makefile"
	@echo
	@echo  "usage: make <target>"
	@echo  "Targets:"
	@echo  "    up      Updates dev/test dependencies"
	@echo  "    deps    Ensure dev/test dependencies are installed"
	@echo  "    check	Checks that build is sane"
	@echo  "    lint	Reports all linter violations"
	@echo  "    test	Runs all tests"
	@echo  "    docs 	Builds the documentation"
	@echo  "    style   Auto-formats the code"

up:
	@poetry update

deps:
	@poetry install -E asyncpg -E aiomysql -E docs

check: deps build
ifneq ($(shell which black),)
	black --check $(black_opts) $(checkfiles) || (echo "Please run 'make style' to auto-fix style issues" && false)
endif
	flake8 $(checkfiles)
	mypy $(checkfiles)
	pylint -d C,W,R $(checkfiles)
	bandit -r $(checkfiles)
	twine check dist/*

lint: deps build
ifneq ($(shell which black),)
	black --check $(black_opts) $(checkfiles) || (echo "Please run 'make style' to auto-fix style issues" && false)
endif
	flake8 $(checkfiles)
	mypy $(checkfiles)
	pylint $(checkfiles)
	bandit -r $(checkfiles)
	twine check dist/*

test: deps
	$(py_warn) TORTOISE_TEST_DB=sqlite://:memory: pytest

test_sqlite:
	$(py_warn) TORTOISE_TEST_DB=sqlite://:memory: pytest --cov-report=

test_postgres:
	python -V | grep PyPy || $(py_warn) TORTOISE_TEST_DB="postgres://postgres:$(TORTOISE_POSTGRES_PASS)@127.0.0.1:5432/test_\{\}" pytest --cov-append --cov-report=

test_mysql_myisam:
	$(py_warn) TORTOISE_TEST_DB="mysql://root:$(TORTOISE_MYSQL_PASS)@127.0.0.1:3306/test_\{\}?storage_engine=MYISAM" pytest --cov-append --cov-report=

test_mysql:
	$(py_warn) TORTOISE_TEST_DB="mysql://root:$(TORTOISE_MYSQL_PASS)@127.0.0.1:3306/test_\{\}" pytest --cov-append --cov-report=

_testall: test_sqlite test_postgres test_mysql_myisam test_mysql

testall: deps _testall
	coverage report

ci: check testall

docs: deps
	rm -fR ./build
	sphinx-build -M html docs build

style: deps
	isort -src $(checkfiles)
	black $(black_opts) $(checkfiles)

build: deps
	rm -fR dist/
	poetry build

publish: deps build
	twine upload dist/*
