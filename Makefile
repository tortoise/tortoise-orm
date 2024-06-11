checkfiles = tortoise/ examples/ tests/ conftest.py
py_warn = PYTHONDEVMODE=1
pytest_opts = -n auto --cov=tortoise --tb=native -q

help:
	@echo  "Tortoise ORM development makefile"
	@echo
	@echo  "usage: make <target>"
	@echo  "Targets:"
	@echo  "    up      Updates dev/test dependencies"
	@echo  "    deps    Ensure dev/test dependencies are installed"
	@echo  "    check	Checks that build is sane"
	@echo  "    test	Runs all tests"
	@echo  "    docs 	Builds the documentation"
	@echo  "    style   Auto-formats the code"

up:
	@poetry update

deps:
	@poetry install -E asyncpg -E aiomysql -E accel -E psycopg -E asyncodbc

_check: build
ifneq ($(shell which black),)
	black --check $(checkfiles) || (echo "Please run 'make style' to auto-fix style issues" && false)
endif
	ruff check $(checkfiles)
	mypy $(checkfiles)
	#pylint -d C,W,R $(checkfiles)
	#bandit -r $(checkfiles)make
	twine check dist/*
check: _deps

lint: deps build
ifneq ($(shell which black),)
	black --check $(checkfiles) || (echo "Please run 'make style' to auto-fix style issues" && false)
endif
	ruff check $(checkfiles)
	mypy $(checkfiles)
	#pylint $(checkfiles)
	bandit -r $(checkfiles)
	twine check dist/*

test: deps
	$(py_warn) TORTOISE_TEST_DB=sqlite://:memory: pytest $(pytest_opts)

test_sqlite:
	$(py_warn) TORTOISE_TEST_DB=sqlite://:memory: pytest --cov-report= $(pytest_opts)

test_postgres_asyncpg:
	python -V | grep PyPy || $(py_warn) TORTOISE_TEST_DB="asyncpg://postgres:$(TORTOISE_POSTGRES_PASS)@127.0.0.1:5432/test_\{\}" pytest $(pytest_opts) --cov-append --cov-report=

test_postgres_psycopg:
	python -V | grep PyPy || $(py_warn) TORTOISE_TEST_DB="psycopg://postgres:$(TORTOISE_POSTGRES_PASS)@127.0.0.1:5432/test_\{\}" pytest $(pytest_opts) --cov-append --cov-report=

test_mysql_myisam:
	$(py_warn) TORTOISE_TEST_DB="mysql://root:$(TORTOISE_MYSQL_PASS)@127.0.0.1:3306/test_\{\}?storage_engine=MYISAM" pytest $(pytest_opts) --cov-append --cov-report=

test_mysql:
	$(py_warn) TORTOISE_TEST_DB="mysql://root:$(TORTOISE_MYSQL_PASS)@127.0.0.1:3306/test_\{\}" pytest $(pytest_opts) --cov-append --cov-report=

test_mssql:
	$(py_warn) TORTOISE_TEST_DB="mssql://sa:$(TORTOISE_MSSQL_PASS)@127.0.0.1:1433/test_\{\}?driver=$(TORTOISE_MSSQL_DRIVER)&TrustServerCertificate=YES" pytest $(pytest_opts) --cov-append --cov-report=

test_oracle:
	$(py_warn) TORTOISE_TEST_DB="oracle://SYSTEM:$(TORTOISE_ORACLE_PASS)@127.0.0.1:1521/test_\{\}?driver=$(TORTOISE_ORACLE_DRIVER)" pytest $(pytest_opts) --cov-append --cov-report=

_testall: test_sqlite test_postgres_asyncpg test_postgres_psycopg test_mysql_myisam test_mysql test_mssql

testall: deps _testall
	coverage report

_ci: _check _testall
ci: deps _ci

docs: deps
	rm -fR ./build
	sphinx-build -M html docs build

style: deps
	isort -src $(checkfiles)
	black $(checkfiles)

build: deps
	rm -fR dist/
	poetry build

publish: deps build
	twine upload dist/*
