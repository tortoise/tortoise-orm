import operator
from unittest import TestCase as _TestCase

from tests.testmodels import CharFields, IntFields
from tortoise.contrib.test import TestCase
from tortoise.exceptions import OperationalError
from tortoise.expressions import F, Q, ResolveContext


class TestQ(_TestCase):
    def test_q_basic(self):
        q = Q(moo="cow")
        self.assertEqual(q.children, ())
        self.assertEqual(q.filters, {"moo": "cow"})
        self.assertEqual(q.join_type, "AND")

    def test_q_compound(self):
        q1 = Q(moo="cow")
        q2 = Q(moo="bull")
        q = Q(q1, q2, join_type=Q.OR)

        self.assertEqual(q1.children, ())
        self.assertEqual(q1.filters, {"moo": "cow"})
        self.assertEqual(q1.join_type, "AND")

        self.assertEqual(q2.children, ())
        self.assertEqual(q2.filters, {"moo": "bull"})
        self.assertEqual(q2.join_type, "AND")

        self.assertEqual(q.children, (q1, q2))
        self.assertEqual(q.filters, {})
        self.assertEqual(q.join_type, "OR")

    def test_q_compound_or(self):
        q1 = Q(moo="cow")
        q2 = Q(moo="bull")
        q = q1 | q2

        self.assertEqual(q1.children, ())
        self.assertEqual(q1.filters, {"moo": "cow"})
        self.assertEqual(q1.join_type, "AND")

        self.assertEqual(q2.children, ())
        self.assertEqual(q2.filters, {"moo": "bull"})
        self.assertEqual(q2.join_type, "AND")

        self.assertEqual(q.children, (q1, q2))
        self.assertEqual(q.filters, {})
        self.assertEqual(q.join_type, "OR")

    def test_q_compound_and(self):
        q1 = Q(moo="cow")
        q2 = Q(moo="bull")
        q = q1 & q2

        self.assertEqual(q1.children, ())
        self.assertEqual(q1.filters, {"moo": "cow"})
        self.assertEqual(q1.join_type, "AND")

        self.assertEqual(q2.children, ())
        self.assertEqual(q2.filters, {"moo": "bull"})
        self.assertEqual(q2.join_type, "AND")

        self.assertEqual(q.children, (q1, q2))
        self.assertEqual(q.filters, {})
        self.assertEqual(q.join_type, "AND")

    def test_q_compound_or_notq(self):
        with self.assertRaisesRegex(OperationalError, "OR operation requires a Q node"):
            Q() | 2  # pylint: disable=W0106

    def test_q_compound_and_notq(self):
        with self.assertRaisesRegex(OperationalError, "AND operation requires a Q node"):
            Q() & 2  # pylint: disable=W0106

    def test_q_notq(self):
        with self.assertRaisesRegex(OperationalError, "All ordered arguments must be Q nodes"):
            Q(Q(), 1)

    def test_q_bad_join_type(self):
        with self.assertRaisesRegex(OperationalError, "join_type must be AND or OR"):
            Q(join_type=3)

    def test_q_partial_and(self):
        q = Q(join_type="AND", moo="cow")
        self.assertEqual(q.children, ())
        self.assertEqual(q.filters, {"moo": "cow"})
        self.assertEqual(q.join_type, "AND")

    def test_q_partial_or(self):
        q = Q(join_type="OR", moo="cow")
        self.assertEqual(q.children, ())
        self.assertEqual(q.filters, {"moo": "cow"})
        self.assertEqual(q.join_type, "OR")

    def test_q_equality(self):
        # basic query
        basic_q1 = Q(moo="cow")
        basic_q2 = Q(moo="cow")
        self.assertEqual(basic_q1, basic_q2)

        # and query
        and_q1 = Q(firstname="John") & Q(lastname="Doe")
        and_q2 = Q(firstname="John") & Q(lastname="Doe")
        self.assertEqual(and_q1, and_q2)

        # or query
        or_q1 = Q(firstname="John") | Q(lastname="Doe")
        or_q2 = Q(firstname="John") | Q(lastname="Doe")
        self.assertEqual(or_q1, or_q2)

        # complex query
        complex_q1 = (Q(firstname="John") & Q(lastname="Doe")) | Q(mother_name="Jane")
        complex_q2 = (Q(firstname="John") & Q(lastname="Doe")) | Q(mother_name="Jane")
        self.assertEqual(complex_q1, complex_q2)


class TestQCall(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.int_fields_context = ResolveContext(
            model=IntFields,
            table=IntFields._meta.basequery,  # type:ignore[arg-type]
            annotations={},
            custom_filters={},
        )
        self.char_fields_context = ResolveContext(
            model=CharFields,
            table=CharFields._meta.basequery,  # type:ignore[arg-type]
            annotations={},
            custom_filters={},
        )

    def test_q_basic(self):
        q = Q(id=8)
        r = q.resolve(self.int_fields_context)
        self.assertEqual(r.where_criterion.get_sql(), '"id"=8')

    def test_q_basic_and(self):
        q = Q(join_type="AND", id=8)
        r = q.resolve(self.int_fields_context)
        self.assertEqual(r.where_criterion.get_sql(), '"id"=8')

    def test_q_basic_or(self):
        q = Q(join_type="OR", id=8)
        r = q.resolve(self.int_fields_context)
        self.assertEqual(r.where_criterion.get_sql(), '"id"=8')

    def test_q_multiple_and(self):
        q = Q(join_type="AND", id__gt=8, id__lt=10)
        r = q.resolve(self.int_fields_context)
        self.assertEqual(r.where_criterion.get_sql(), '"id">8 AND "id"<10')

    def test_q_multiple_or(self):
        q = Q(join_type="OR", id__gt=8, id__lt=10)
        r = q.resolve(self.int_fields_context)
        self.assertEqual(r.where_criterion.get_sql(), '"id">8 OR "id"<10')

    def test_q_multiple_and2(self):
        q = Q(join_type="AND", id=8, intnum=80)
        r = q.resolve(self.int_fields_context)
        self.assertEqual(r.where_criterion.get_sql(), '"id"=8 AND "intnum"=80')

    def test_q_multiple_or2(self):
        q = Q(join_type="OR", id=8, intnum=80)
        r = q.resolve(self.int_fields_context)
        self.assertEqual(r.where_criterion.get_sql(), '"id"=8 OR "intnum"=80')

    def test_q_complex_int(self):
        q = Q(Q(intnum=80), Q(id__lt=5, id__gt=50, join_type="OR"), join_type="AND")
        r = q.resolve(self.int_fields_context)
        self.assertEqual(r.where_criterion.get_sql(), '"intnum"=80 AND ("id"<5 OR "id">50)')

    def test_q_complex_int2(self):
        q = Q(Q(intnum="80"), Q(Q(id__lt="5"), Q(id__gt="50"), join_type="OR"), join_type="AND")
        r = q.resolve(self.int_fields_context)
        self.assertEqual(r.where_criterion.get_sql(), '"intnum"=80 AND ("id"<5 OR "id">50)')

    def test_q_complex_int3(self):
        q = Q(Q(id__lt=5, id__gt=50, join_type="OR"), join_type="AND", intnum=80)
        r = q.resolve(self.int_fields_context)
        self.assertEqual(r.where_criterion.get_sql(), '"intnum"=80 AND ("id"<5 OR "id">50)')

    def test_q_complex_char(self):
        q = Q(Q(char_null=80), ~Q(char__lt=5, char__gt=50, join_type="OR"), join_type="AND")
        r = q.resolve(self.char_fields_context)
        self.assertEqual(
            r.where_criterion.get_sql(),
            "\"char_null\"='80' AND NOT (\"char\"<'5' OR \"char\">'50')",
        )

    def test_q_complex_char2(self):
        q = Q(
            Q(char_null="80"),
            ~Q(Q(char__lt="5"), Q(char__gt="50"), join_type="OR"),
            join_type="AND",
        )
        r = q.resolve(self.char_fields_context)
        self.assertEqual(
            r.where_criterion.get_sql(),
            "\"char_null\"='80' AND NOT (\"char\"<'5' OR \"char\">'50')",
        )

    def test_q_complex_char3(self):
        q = Q(~Q(char__lt=5, char__gt=50, join_type="OR"), join_type="AND", char_null=80)
        r = q.resolve(self.char_fields_context)
        self.assertEqual(
            r.where_criterion.get_sql(),
            "\"char_null\"='80' AND NOT (\"char\"<'5' OR \"char\">'50')",
        )

    def test_q_with_blank_and(self):
        q = Q(Q(id__gt=5), Q(), join_type=Q.AND)
        r = q.resolve(self.char_fields_context)
        self.assertEqual(r.where_criterion.get_sql(), '"id">5')

    def test_q_with_blank_or(self):
        q = Q(Q(id__gt=5), Q(), join_type=Q.OR)
        r = q.resolve(self.char_fields_context)
        self.assertEqual(r.where_criterion.get_sql(), '"id">5')

    def test_q_with_blank_and2(self):
        q = Q(id__gt=5) & Q()
        r = q.resolve(self.char_fields_context)
        self.assertEqual(r.where_criterion.get_sql(), '"id">5')

    def test_q_with_blank_or2(self):
        q = Q(id__gt=5) | Q()
        r = q.resolve(self.char_fields_context)
        self.assertEqual(r.where_criterion.get_sql(), '"id">5')

    def test_q_with_blank_and3(self):
        q = Q() & Q(id__gt=5)
        r = q.resolve(self.char_fields_context)
        self.assertEqual(r.where_criterion.get_sql(), '"id">5')

    def test_q_with_blank_or3(self):
        q = Q() | Q(id__gt=5)
        r = q.resolve(self.char_fields_context)
        self.assertEqual(r.where_criterion.get_sql(), '"id">5')

    def test_annotations_resolved(self):
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
        self.assertEqual(r.where_criterion.get_sql(), '"id">5 OR "intnum"<5')
