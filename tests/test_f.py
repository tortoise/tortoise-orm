from tortoise.contrib import test
from tortoise.expressions import Connector, F


class TestF(test.TestCase):
    def test_arithmetic(self):
        f = F("name")

        negated = -f
        self.assertEqual(negated.connector, Connector.mul)
        self.assertEqual(negated.right.value, -1)

        added = f + 1
        self.assertEqual(added.connector, Connector.add)
        self.assertEqual(added.right.value, 1)

        radded = 1 + f
        self.assertEqual(radded.connector, Connector.add)
        self.assertEqual(radded.left.value, 1)
        self.assertEqual(radded.right, f)

        subbed = f - 1
        self.assertEqual(subbed.connector, Connector.sub)
        self.assertEqual(subbed.right.value, 1)

        rsubbed = 1 - f
        self.assertEqual(rsubbed.connector, Connector.sub)
        self.assertEqual(rsubbed.left.value, 1)

        mulled = f * 2
        self.assertEqual(mulled.connector, Connector.mul)
        self.assertEqual(mulled.right.value, 2)

        rmulled = 2 * f
        self.assertEqual(rmulled.connector, Connector.mul)
        self.assertEqual(rmulled.left.value, 2)

        divved = f / 2
        self.assertEqual(divved.connector, Connector.div)
        self.assertEqual(divved.right.value, 2)

        rdivved = 2 / f
        self.assertEqual(rdivved.connector, Connector.div)
        self.assertEqual(rdivved.left.value, 2)

        powed = f**2
        self.assertEqual(powed.connector, Connector.pow)
        self.assertEqual(powed.right.value, 2)

        rpowed = 2**f
        self.assertEqual(rpowed.connector, Connector.pow)
        self.assertEqual(rpowed.left.value, 2)

        modded = f % 2
        self.assertEqual(modded.connector, Connector.mod)
        self.assertEqual(modded.right.value, 2)

        rmodded = 2 % f
        self.assertEqual(rmodded.connector, Connector.mod)
        self.assertEqual(rmodded.left.value, 2)
