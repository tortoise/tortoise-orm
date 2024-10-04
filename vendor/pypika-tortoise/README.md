# pypika-tortoise

[![image](https://img.shields.io/pypi/v/pypika-tortoise.svg?style=flat)](https://pypi.python.org/pypi/pypika-tortoise)
[![image](https://img.shields.io/github/license/tortoise/pypika-tortoise)](https://github.com/tortoise/pypika-tortoise)
[![image](https://github.com/tortoise/pypika-tortoise/workflows/pypi/badge.svg)](https://github.com/tortoise/pypika-tortoise/actions?query=workflow:pypi)
[![image](https://github.com/tortoise/pypika-tortoise/workflows/ci/badge.svg)](https://github.com/tortoise/pypika-tortoise/actions?query=workflow:ci)

Forked from [pypika](https://github.com/kayak/pypika) and streamline just for tortoise-orm.

## Why forked?

The original repo include many databases that tortoise-orm don't need, and which aims to be a perfect sql builder and
should consider more compatibilities, but tortoise-orm is not, and we need add new features and update it ourselves.

## What change?

Delete many codes that tortoise-orm don't need, and add features just tortoise-orm considers to.

## What affect tortoise-orm?

Nothing, because this repo keeps the original struct and code.

## ThanksTo

- [pypika](https://github.com/kayak/pypika), a python SQL query builder that exposes the full richness of the SQL
  language using a syntax that reflects the resulting query.

## License

This project is licensed under the [Apache-2.0](./LICENSE) License.
