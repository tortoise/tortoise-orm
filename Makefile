checkfiles = tortoise/ examples/ tests/ conftest.py
py_warn = PYTHONDEVMODE=1
pytest_opts = -n auto --cov=tortoise --cov-append --cov-branch --tb=native -q

TORTOISE_MYSQL_PASS ?= 123456
TORTOISE_POSTGRES_PASS ?= 123456
TORTOISE_MSSQL_PASS ?= 123456
TORTOISE_ORACLE_PASS ?= 123456

help:
	@echo  "Tortoise ORM development makefile"
	@echo
	@echo  "usage: make <target>"
	@echo  "Targets:"
	@echo  "    up      Updates dev/test dependencies"
	@echo  "    deps    Ensure dev/test dependencies are installed"
	@echo  "    check   Checks that build is sane"
	@echo  "    test    Runs all tests"
	@echo  "    docs    Builds the documentation"
	@echo  "    style   Auto-formats the code"
	@echo  "    lint    Auto-formats the code and check type hints"

up:
	@poetry update

deps:
	@poetry install --all-groups -E asyncpg -E accel -E psycopg -E asyncodbc -E aiomysql

deps_with_asyncmy:
	@poetry install --all-groups -E asyncpg -E accel -E psycopg -E asyncodbc -E asyncmy

check: build _check
_check:
	ruff format --check $(checkfiles) || (echo "Please run 'make style' to auto-fix style issues" && false)
	ruff check $(checkfiles)
	#pylint -d C,W,R $(checkfiles)
	$(MAKE) _codeqc

style: deps _style
_style:
	ruff format $(checkfiles)
	ruff check --fix $(checkfiles)

lint: build _lint
_lint:
	$(MAKE) _style
	$(MAKE) _codeqc

codeqc: build _typehints
_codeqc:
	mypy $(checkfiles)
	bandit -c pyproject.toml -r $(checkfiles)
	twine check dist/*

test: deps
	$(py_warn) TORTOISE_TEST_DB=sqlite://:memory: pytest $(pytest_opts)

test_sqlite:
	$(py_warn) TORTOISE_TEST_DB=sqlite://:memory: pytest --cov-report= $(pytest_opts)

test_sqlite_regexp:
	$(py_warn) TORTOISE_TEST_DB=sqlite://:memory:?install_regexp_functions=True pytest --cov-report= $(pytest_opts)

test_postgres_asyncpg:
	python -V | grep PyPy || $(py_warn) TORTOISE_TEST_DB="asyncpg://postgres:$(TORTOISE_POSTGRES_PASS)@127.0.0.1:5432/test_\{\}" pytest $(pytest_opts) --cov-report=

test_postgres_psycopg:
	python -V | grep PyPy || $(py_warn) TORTOISE_TEST_DB="psycopg://postgres:$(TORTOISE_POSTGRES_PASS)@127.0.0.1:5432/test_\{\}" pytest $(pytest_opts) --cov-report=

test_mysql_myisam:
	$(py_warn) TORTOISE_TEST_DB="mysql://root:$(TORTOISE_MYSQL_PASS)@127.0.0.1:3306/test_\{\}?storage_engine=MYISAM" pytest $(pytest_opts) --cov-report=

test_mysql:
	$(py_warn) TORTOISE_TEST_DB="mysql://root:$(TORTOISE_MYSQL_PASS)@127.0.0.1:3306/test_\{\}" pytest $(pytest_opts) --cov-report=

test_mysql_asyncmy:
	$(MAKE) deps_with_asyncmy
	$(MAKE) test_mysql
	# Restore dependencies to the default
	$(MAKE) deps

test_mssql:
	$(py_warn) TORTOISE_TEST_DB="mssql://sa:$(TORTOISE_MSSQL_PASS)@127.0.0.1:1433/test_\{\}?driver=$(TORTOISE_MSSQL_DRIVER)&TrustServerCertificate=YES" pytest $(pytest_opts) --cov-report=

test_oracle:
	$(py_warn) TORTOISE_TEST_DB="oracle://SYSTEM:$(TORTOISE_ORACLE_PASS)@127.0.0.1:1521/test_\{\}?driver=$(TORTOISE_ORACLE_DRIVER)" pytest $(pytest_opts) --cov-report=

_testall: test_sqlite test_postgres_asyncpg test_postgres_psycopg test_mysql_myisam test_mysql test_mysql_asyncmy test_mssql

	coverage report

testall: deps _testall

ci: check _testall

docs: deps
	rm -fR ./build
	sphinx-build -M html docs build

build: deps
	rm -fR dist/
	poetry build

publish: deps _build
	twine upload dist/*
