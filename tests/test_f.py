from tests.testmodels import JSONFields
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

    @test.requireCapability(support_json_attributes=True)
    async def test_values_with_json_field_attribute(self):
        await JSONFields.create(data='{"attribute": 1}')
        res = await JSONFields.annotate(attribute=F("data__attribute")).first()
        self.assertEqual(int(res.attribute), 1)

    @test.requireCapability(support_json_attributes=True)
    async def test_values_with_json_field_attribute_of_attribute(self):
        await JSONFields.create(data='{"attribute": {"subattribute": "value"}}')
        res = await JSONFields.annotate(subattribute=F("data__attribute__subattribute")).first()
        self.assertEqual(res.subattribute, "value")

    @test.requireCapability(support_json_attributes=True)
    async def test_values_with_json_field_str_array_element(self):
        await JSONFields.create(data='["a", "b", "c"]')
        res = await JSONFields.annotate(array_element=F("data__0")).first()
        self.assertEqual(res.array_element, "a")
        res = await JSONFields.annotate(array_element=F("data__1")).first()
        self.assertEqual(res.array_element, "b")
        res = await JSONFields.annotate(array_element=F("data__2")).first()
        self.assertEqual(res.array_element, "c")
        res = await JSONFields.annotate(array_element=F("data__3")).first()
        self.assertIsNone(res.array_element)

    @test.requireCapability(support_json_attributes=True)
    async def test_values_with_json_field_array_attribute(self):
        await JSONFields.create(data='{"array": ["a", "b", "c"]}')
        res = await JSONFields.annotate(array_attribute=F("data__array__0")).first()
        self.assertEqual(res.array_attribute, "a")
        res = await JSONFields.annotate(array_attribute=F("data__array__1")).first()
        self.assertEqual(res.array_attribute, "b")
        res = await JSONFields.annotate(array_attribute=F("data__array__2")).first()
        self.assertEqual(res.array_attribute, "c")

    @test.requireCapability(support_json_attributes=True)
    async def test_values_with_json_field_int_array_element(self):
        """
        Among the supported dialects, only SQLite will return the correct type.
        """
        await JSONFields.create(data="[1, 2, 3]")
        res = await JSONFields.annotate(array_element=F("data__0")).first()
        self.assertEqual(int(res.array_element), 1)
        res = await JSONFields.annotate(array_element=F("data__1")).first()
        self.assertEqual(int(res.array_element), 2)
        res = await JSONFields.annotate(array_element=F("data__2")).first()
        self.assertEqual(int(res.array_element), 3)
        res = await JSONFields.annotate(array_element=F("data__3")).first()
        self.assertIsNone(res.array_element)

    @test.requireCapability(support_json_attributes=True)
    async def test_filter_with_json_field_attribute(self):
        exp = await JSONFields.create(data='{"attribute": "a"}')
        res = (
            await JSONFields.annotate(attribute=F("data__attribute")).filter(attribute="a").first()
        )
        self.assertEqual(res.id, exp.id)
        res = (
            await JSONFields.annotate(attribute=F("data__attribute")).filter(attribute="b").first()
        )
        self.assertIsNone(res)

    @test.requireCapability(support_json_attributes=True)
    async def test_filter_with_json_field_attribute_of_attribute(self):
        exp = await JSONFields.create(data='{"attribute": {"subattribute": "value"}}')
        res = (
            await JSONFields.annotate(subattribute=F("data__attribute__subattribute"))
            .filter(subattribute="value")
            .first()
        )
        self.assertEqual(res.id, exp.id)

    @test.requireCapability(support_json_attributes=True)
    async def test_filter_with_json_field_str_array_element(self):
        exp = await JSONFields.create(data='["a", "b", "c"]')
        res = (
            await JSONFields.annotate(array_element=F("data__0")).filter(array_element="a").first()
        )
        self.assertEqual(res.id, exp.id)
        res = (
            await JSONFields.annotate(array_element=F("data__1")).filter(array_element="b").first()
        )
        self.assertEqual(res.id, exp.id)
