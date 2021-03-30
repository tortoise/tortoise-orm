from typing import Optional, Set

from pypika.terms import Term

from tortoise.indexes import Index


class FullTextIndex(Index):
    INDEX_TYPE = "FULLTEXT"

    def __init__(
        self,
        *expressions: Term,
        fields: Optional[Set[str]] = None,
        name: Optional[str] = None,
        parser_name: Optional[str] = None,
    ):
        super().__init__(*expressions, fields=fields, name=name)
        if parser_name:
            self.extra = f" WITH PARSER {parser_name}"


class SpatialIndex(Index):
    INDEX_TYPE = "SPATIAL"
