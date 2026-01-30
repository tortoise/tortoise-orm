import operator

import pytest
from pypika_tortoise.context import DEFAULT_SQL_CONTEXT

from tests.testmodels import CharFields, IntFields
from tortoise.exceptions import OperationalError
from tortoise.expressions import F, Q, ResolveContext

# =============================================================================
# Tests for Q object basic operations (no database needed)
# =============================================================================


def test_q_basic():
    q = Q(moo="cow")
    assert q.children == ()
    assert q.filters == {"moo": "cow"}
    assert q.join_type == "AND"


def test_q_compound():
    q1 = Q(moo="cow")
    q2 = Q(moo="bull")
    q = Q(q1, q2, join_type=Q.OR)

    assert q1.children == ()
    assert q1.filters == {"moo": "cow"}
    assert q1.join_type == "AND"

    assert q2.children == ()
    assert q2.filters == {"moo": "bull"}
    assert q2.join_type == "AND"

    assert q.children == (q1, q2)
    assert q.filters == {}
    assert q.join_type == "OR"


def test_q_compound_or():
    q1 = Q(moo="cow")
    q2 = Q(moo="bull")
    q = q1 | q2

    assert q1.children == ()
    assert q1.filters == {"moo": "cow"}
    assert q1.join_type == "AND"

    assert q2.children == ()
    assert q2.filters == {"moo": "bull"}
    assert q2.join_type == "AND"

    assert q.children == (q1, q2)
    assert q.filters == {}
    assert q.join_type == "OR"


def test_q_compound_and():
    q1 = Q(moo="cow")
    q2 = Q(moo="bull")
    q = q1 & q2

    assert q1.children == ()
    assert q1.filters == {"moo": "cow"}
    assert q1.join_type == "AND"

    assert q2.children == ()
    assert q2.filters == {"moo": "bull"}
    assert q2.join_type == "AND"

    assert q.children == (q1, q2)
    assert q.filters == {}
    assert q.join_type == "AND"


def test_q_compound_or_notq():
    with pytest.raises(OperationalError, match="OR operation requires a Q node"):
        Q() | 2  # pylint: disable=W0106


def test_q_compound_and_notq():
    with pytest.raises(OperationalError, match="AND operation requires a Q node"):
        Q() & 2  # pylint: disable=W0106


def test_q_notq():
    with pytest.raises(OperationalError, match="All ordered arguments must be Q nodes"):
        Q(Q(), 1)


def test_q_bad_join_type():
    with pytest.raises(OperationalError, match="join_type must be AND or OR"):
        Q(join_type=3)


def test_q_partial_and():
    q = Q(join_type="AND", moo="cow")
    assert q.children == ()
    assert q.filters == {"moo": "cow"}
    assert q.join_type == "AND"


def test_q_partial_or():
    q = Q(join_type="OR", moo="cow")
    assert q.children == ()
    assert q.filters == {"moo": "cow"}
    assert q.join_type == "OR"


def test_q_equality():
    # basic query
    basic_q1 = Q(moo="cow")
    basic_q2 = Q(moo="cow")
    assert basic_q1 == basic_q2

    # and query
    and_q1 = Q(firstname="John") & Q(lastname="Doe")
    and_q2 = Q(firstname="John") & Q(lastname="Doe")
    assert and_q1 == and_q2

    # or query
    or_q1 = Q(firstname="John") | Q(lastname="Doe")
    or_q2 = Q(firstname="John") | Q(lastname="Doe")
    assert or_q1 == or_q2

    # complex query
    complex_q1 = (Q(firstname="John") & Q(lastname="Doe")) | Q(mother_name="Jane")
    complex_q2 = (Q(firstname="John") & Q(lastname="Doe")) | Q(mother_name="Jane")
    assert complex_q1 == complex_q2


# =============================================================================
# Tests for Q object resolution (requires database for model resolution)
# =============================================================================


@pytest.fixture
def int_fields_context(db):
    """Context for IntFields model resolution."""
    return ResolveContext(
        model=IntFields,
        table=IntFields._meta.basequery,
        annotations={},
        custom_filters={},
    )


@pytest.fixture
def char_fields_context(db):
    """Context for CharFields model resolution."""
    return ResolveContext(
        model=CharFields,
        table=CharFields._meta.basequery,
        annotations={},
        custom_filters={},
    )


def test_q_call_basic(int_fields_context):
    q = Q(id=8)
    r = q.resolve(int_fields_context)
    assert r.where_criterion.get_sql(DEFAULT_SQL_CONTEXT) == '"id"=8'


def test_q_call_basic_and(int_fields_context):
    q = Q(join_type="AND", id=8)
    r = q.resolve(int_fields_context)
    assert r.where_criterion.get_sql(DEFAULT_SQL_CONTEXT) == '"id"=8'


def test_q_call_basic_or(int_fields_context):
    q = Q(join_type="OR", id=8)
    r = q.resolve(int_fields_context)
    assert r.where_criterion.get_sql(DEFAULT_SQL_CONTEXT) == '"id"=8'


def test_q_call_multiple_and(int_fields_context):
    q = Q(join_type="AND", id__gt=8, id__lt=10)
    r = q.resolve(int_fields_context)
    assert r.where_criterion.get_sql(DEFAULT_SQL_CONTEXT) == '"id">8 AND "id"<10'


def test_q_call_multiple_or(int_fields_context):
    q = Q(join_type="OR", id__gt=8, id__lt=10)
    r = q.resolve(int_fields_context)
    assert r.where_criterion.get_sql(DEFAULT_SQL_CONTEXT) == '"id">8 OR "id"<10'


def test_q_call_multiple_and2(int_fields_context):
    q = Q(join_type="AND", id=8, intnum=80)
    r = q.resolve(int_fields_context)
    assert r.where_criterion.get_sql(DEFAULT_SQL_CONTEXT) == '"id"=8 AND "intnum"=80'


def test_q_call_multiple_or2(int_fields_context):
    q = Q(join_type="OR", id=8, intnum=80)
    r = q.resolve(int_fields_context)
    assert r.where_criterion.get_sql(DEFAULT_SQL_CONTEXT) == '"id"=8 OR "intnum"=80'


def test_q_call_complex_int(int_fields_context):
    q = Q(Q(intnum=80), Q(id__lt=5, id__gt=50, join_type="OR"), join_type="AND")
    r = q.resolve(int_fields_context)
    assert r.where_criterion.get_sql(DEFAULT_SQL_CONTEXT) == '"intnum"=80 AND ("id"<5 OR "id">50)'


def test_q_call_complex_int2(int_fields_context):
    q = Q(Q(intnum="80"), Q(Q(id__lt="5"), Q(id__gt="50"), join_type="OR"), join_type="AND")
    r = q.resolve(int_fields_context)
    assert r.where_criterion.get_sql(DEFAULT_SQL_CONTEXT) == '"intnum"=80 AND ("id"<5 OR "id">50)'


def test_q_call_complex_int3(int_fields_context):
    q = Q(Q(id__lt=5, id__gt=50, join_type="OR"), join_type="AND", intnum=80)
    r = q.resolve(int_fields_context)
    assert r.where_criterion.get_sql(DEFAULT_SQL_CONTEXT) == '"intnum"=80 AND ("id"<5 OR "id">50)'


def test_q_call_complex_char(char_fields_context):
    q = Q(Q(char_null=80), ~Q(char__lt=5, char__gt=50, join_type="OR"), join_type="AND")
    r = q.resolve(char_fields_context)
    assert (
        r.where_criterion.get_sql(DEFAULT_SQL_CONTEXT)
        == "\"char_null\"='80' AND NOT (\"char\"<'5' OR \"char\">'50')"
    )


def test_q_call_complex_char2(char_fields_context):
    q = Q(
        Q(char_null="80"),
        ~Q(Q(char__lt="5"), Q(char__gt="50"), join_type="OR"),
        join_type="AND",
    )
    r = q.resolve(char_fields_context)
    assert (
        r.where_criterion.get_sql(DEFAULT_SQL_CONTEXT)
        == "\"char_null\"='80' AND NOT (\"char\"<'5' OR \"char\">'50')"
    )


def test_q_call_complex_char3(char_fields_context):
    q = Q(~Q(char__lt=5, char__gt=50, join_type="OR"), join_type="AND", char_null=80)
    r = q.resolve(char_fields_context)
    assert (
        r.where_criterion.get_sql(DEFAULT_SQL_CONTEXT)
        == "\"char_null\"='80' AND NOT (\"char\"<'5' OR \"char\">'50')"
    )


def test_q_call_with_blank_and(char_fields_context):
    q = Q(Q(id__gt=5), Q(), join_type=Q.AND)
    r = q.resolve(char_fields_context)
    assert r.where_criterion.get_sql(DEFAULT_SQL_CONTEXT) == '"id">5'


def test_q_call_with_blank_or(char_fields_context):
    q = Q(Q(id__gt=5), Q(), join_type=Q.OR)
    r = q.resolve(char_fields_context)
    assert r.where_criterion.get_sql(DEFAULT_SQL_CONTEXT) == '"id">5'


def test_q_call_with_blank_and2(char_fields_context):
    q = Q(id__gt=5) & Q()
    r = q.resolve(char_fields_context)
    assert r.where_criterion.get_sql(DEFAULT_SQL_CONTEXT) == '"id">5'


def test_q_call_with_blank_or2(char_fields_context):
    q = Q(id__gt=5) | Q()
    r = q.resolve(char_fields_context)
    assert r.where_criterion.get_sql(DEFAULT_SQL_CONTEXT) == '"id">5'


def test_q_call_with_blank_and3(char_fields_context):
    q = Q() & Q(id__gt=5)
    r = q.resolve(char_fields_context)
    assert r.where_criterion.get_sql(DEFAULT_SQL_CONTEXT) == '"id">5'


def test_q_call_with_blank_or3(char_fields_context):
    q = Q() | Q(id__gt=5)
    r = q.resolve(char_fields_context)
    assert r.where_criterion.get_sql(DEFAULT_SQL_CONTEXT) == '"id">5'


def test_q_call_annotations_resolved(db):
    q = Q(id__gt=5) | Q(annotated__lt=5)
    r = q.resolve(
        ResolveContext(
            model=IntFields,
            table=IntFields._meta.basequery,
            annotations={"annotated": F("intnum")},
            custom_filters={
                "annotated__lt": {
                    "field": "annotated",
                    "source_field": "annotated",
                    "operator": operator.lt,
                }
            },
        )
    )
    assert r.where_criterion.get_sql(DEFAULT_SQL_CONTEXT) == '"id">5 OR "intnum"<5'
