from tortoise.contrib import test
from tortoise.tests_gis.testmodels import GeometryFields
from shapely.geometry import Point


class TestRegistry(test.TestCase):

    async def test_insert(self):
        point = await GeometryFields.create(name="London Eye", location=Point(0, 0))
        area = await GeometryFields.create(name="London", area=Point(0, 0).buffer(10))
        database_points = await GeometryFields.all()
        pass
