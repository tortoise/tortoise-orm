"""
Implements arbitrary SQL functions using getattr.

Inspired by the SQLAlchemy function implementation.
"""

from pypika.functions import Function as PyPikaFunction
from pypika.terms import Criterion, Field
from tortoise.query_utils import Q, QueryModifier


class FunctionCriterion(Criterion):

    def __init__(self, function: 'Function', alias=None):
        super().__init__(alias)
        self.function = function

    def fields(self):
        return [x for x in self.function.args if isinstance(x, Field)]

    def get_sql(self, with_alias=False, **kwargs):
        sql = self.function.get_function_sql()
        if with_alias and self.alias:
            return '{sql} "{alias}"'.format(sql=sql, alias=self.alias)
        return sql


class Function(PyPikaFunction, Q):
    def __init__(self, name, *args, **kwargs):
        PyPikaFunction.__init__(self, name, *args, **kwargs)
        Q.__init__(self)

    def resolve(self, model, annotations, custom_filters):
        return QueryModifier(where_criterion=FunctionCriterion(self))


class _FunctionBuilder:

    def __init__(self, name=None):
        self.name = name

    def __call__(self, *args, **kwargs):
        return Function(self.name, *args, **kwargs)

    def __getattr__(self, name):
        return _FunctionBuilder(name)


func = _FunctionBuilder()
