from unittest import TestCase

from tortoise.exceptions import OperationalError
from tortoise.query_utils import Q


class TestQ(TestCase):

    def test_q_basic(self):
        q = Q(moo='cow')
        self.assertEqual(q.children, ())
        self.assertEqual(q.filters, {'moo': 'cow'})
        self.assertEqual(q.join_type, 'AND')

    def test_q_compound(self):
        q1 = Q(moo='cow')
        q2 = Q(moo='bull')
        q = Q(q1, q2, join_type=Q.OR)

        self.assertEqual(q1.children, ())
        self.assertEqual(q1.filters, {'moo': 'cow'})
        self.assertEqual(q1.join_type, 'AND')

        self.assertEqual(q2.children, ())
        self.assertEqual(q2.filters, {'moo': 'bull'})
        self.assertEqual(q2.join_type, 'AND')

        self.assertEqual(q.children, (q1, q2))
        self.assertEqual(q.filters, {})
        self.assertEqual(q.join_type, 'OR')

    def test_q_compound_or(self):
        q1 = Q(moo='cow')
        q2 = Q(moo='bull')
        q = q1 | q2

        self.assertEqual(q1.children, ())
        self.assertEqual(q1.filters, {'moo': 'cow'})
        self.assertEqual(q1.join_type, 'AND')

        self.assertEqual(q2.children, ())
        self.assertEqual(q2.filters, {'moo': 'bull'})
        self.assertEqual(q2.join_type, 'AND')

        self.assertEqual(q.children, (q1, q2))
        self.assertEqual(q.filters, {})
        self.assertEqual(q.join_type, 'OR')

    def test_q_compound_and(self):
        q1 = Q(moo='cow')
        q2 = Q(moo='bull')
        q = q1 & q2

        self.assertEqual(q1.children, ())
        self.assertEqual(q1.filters, {'moo': 'cow'})
        self.assertEqual(q1.join_type, 'AND')

        self.assertEqual(q2.children, ())
        self.assertEqual(q2.filters, {'moo': 'bull'})
        self.assertEqual(q2.join_type, 'AND')

        self.assertEqual(q.children, (q1, q2))
        self.assertEqual(q.filters, {})
        self.assertEqual(q.join_type, 'AND')

    def test_q_compound_or_notq(self):
        with self.assertRaisesRegex(OperationalError, 'OR operation requires a Q node'):
            Q() | 2  # pylint: disable=W0106

    def test_q_compound_and_notq(self):
        with self.assertRaisesRegex(OperationalError, 'AND operation requires a Q node'):
            Q() & 2  # pylint: disable=W0106

    def test_q_both(self):
        with self.assertRaisesRegex(OperationalError,
                                    'You can pass only Q nodes or filter kwargs in one Q node'):
            Q(Q(), moo='cow')

    def test_q_notq(self):
        with self.assertRaisesRegex(OperationalError, 'All ordered arguments must be Q nodes'):
            Q(Q(), 1)

    def test_q_bad_join_type(self):
        with self.assertRaisesRegex(OperationalError,
                                    'join_type must be AND or OR'):
            Q(join_type=3)
