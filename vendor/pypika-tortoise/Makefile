checkfiles = pypika/ tests/ conftest.py
black_opts = -l 100 -t py37
py_warn = PYTHONDEVMODE=1

up:
	@poetry update

deps:
	@poetry install

check: deps build
ifneq ($(shell which black),)
	black --check $(black_opts) $(checkfiles) || (echo "Please run 'make style' to auto-fix style issues" && false)
endif
	ruff $(checkfiles)
	twine check dist/*

test: deps
	$(py_warn) pytest

ci: check test

style: deps
	isort -src $(checkfiles)
	black $(black_opts) $(checkfiles)

build: deps
	rm -fR dist/
	poetry build

publish: deps build
	twine upload dist/*
