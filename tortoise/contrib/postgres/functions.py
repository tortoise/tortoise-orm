from pypika.terms import Function, Term


class ToTsVector(Function):  # type: ignore
    """
    to to_tsvector function
    """

    def __init__(self, field: Term):
        super(ToTsVector, self).__init__("TO_TSVECTOR", field)


class ToTsQuery(Function):  # type: ignore
    """
    to_tsquery function
    """

    def __init__(self, field: Term):
        super(ToTsQuery, self).__init__("TO_TSQUERY", field)
