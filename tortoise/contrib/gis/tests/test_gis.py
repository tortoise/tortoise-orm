from shapely.geometry import Point

from tortoise.contrib import test
from tortoise.contrib.gis.gis_functions import Within
from tortoise.contrib.gis.tests.testmodels import GeometryFields


class TestRegistry(test.TestCase):

    async def test_insert(self):
        london = await GeometryFields.create(name="London", area=Point(0, 0).buffer(10))
        fetched_london = await GeometryFields.filter(name="London").first()
        assert fetched_london.area is not None
        assert london == fetched_london

        london_eye = await GeometryFields.create(name="London Eye", location=Point(25, 12))
        fetched_london_eye = await GeometryFields.filter(name="London Eye").first()
        assert fetched_london_eye.location is not None
        assert fetched_london_eye == london_eye

        areas = await GeometryFields.all()
        assert len(areas) == 2
        assert fetched_london_eye in areas
        assert fetched_london in areas

    async def test_filter(self):
        london_eye = await GeometryFields.create(name="London Eye", location=Point(25, 12))
        london = await GeometryFields.create(name="London", area=london_eye.location.buffer(10))
        edinburgh_castle = await GeometryFields.create(name="Edinburgh Castle",
                                                       location=Point(300, 22))

        points_inside_london = await GeometryFields.filter(
            Within(location=london.area),
            location__isnull=False
        )

        assert len(points_inside_london) == 1
        assert london_eye in points_inside_london
        assert edinburgh_castle not in points_inside_london
