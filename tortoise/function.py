"""
Implements arbitrary SQL functions using getattr.

Inspired by the SQLAlchemy function implementation.
"""

from pypika.functions import Function


class _FunctionBuilder:

    def __init__(self, name=None):
        self.name = name

    def __call__(self, *args, **kwargs):
        return Function(self.name, *args, **kwargs)

    def __getattr__(self, name):
        return _FunctionBuilder(name)


func = _FunctionBuilder()