from pypika.terms import Function, Term


class ToTsVector(Function):
    def __init__(self, field: Term):
        super(ToTsVector, self).__init__("TO_TSVECTOR", field)


class ToTsQuery(Function):
    def __init__(self, field: Term):
        super(ToTsQuery, self).__init__("TO_TSQUERY", field)
