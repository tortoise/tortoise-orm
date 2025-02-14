from tests.testmodels import Author, Book, Event, Team, Tournament
from tortoise.contrib import test
from tortoise.functions import Avg, Count, Sum, Upper


class TestGroupBy(test.TestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.a1 = await Author.create(name="author1")
        self.a2 = await Author.create(name="author2")
        self.books1 = [
            await Book.create(name=f"book{i}", author=self.a1, rating=i) for i in range(10)
        ]
        self.books2 = [
            await Book.create(name=f"book{i}", author=self.a2, rating=i) for i in range(5)
        ]

    async def test_count_group_by(self):
        ret = (
            await Book.annotate(count=Count("id"))
            .group_by("author_id")
            .values("author_id", "count")
        )

        for item in ret:
            author_id = item.get("author_id")
            count = item.get("count")
            if author_id == self.a1.pk:
                self.assertEqual(count, 10)
            elif author_id == self.a2.pk:
                self.assertEqual(count, 5)

    async def test_count_group_by_with_join(self):
        ret = (
            await Book.annotate(count=Count("id"))
            .group_by("author__name")
            .values("author__name", "count")
        )
        self.assertListSortEqual(
            ret,
            [{"author__name": "author1", "count": 10}, {"author__name": "author2", "count": 5}],
            sorted_key="author__name",
        )

    async def test_count_filter_group_by(self):
        ret = (
            await Book.annotate(count=Count("id"))
            .filter(count__gt=6)
            .group_by("author_id")
            .values("author_id", "count")
        )
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0].get("count"), 10)

    async def test_sum_group_by(self):
        ret = (
            await Book.annotate(sum=Sum("rating")).group_by("author_id").values("author_id", "sum")
        )
        for item in ret:
            author_id = item.get("author_id")
            sum_ = item.get("sum")
            if author_id == self.a1.pk:
                self.assertEqual(sum_, 45.0)
            elif author_id == self.a2.pk:
                self.assertEqual(sum_, 10.0)

    async def test_sum_group_by_with_join(self):
        ret = (
            await Book.annotate(sum=Sum("rating"))
            .group_by("author__name")
            .values("author__name", "sum")
        )
        self.assertListSortEqual(
            ret,
            [{"author__name": "author1", "sum": 45.0}, {"author__name": "author2", "sum": 10.0}],
            sorted_key="author__name",
        )

    async def test_sum_filter_group_by(self):
        ret = (
            await Book.annotate(sum=Sum("rating"))
            .filter(sum__gt=11)
            .group_by("author_id")
            .values("author_id", "sum")
        )
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0].get("sum"), 45.0)

    async def test_avg_group_by(self):
        ret = (
            await Book.annotate(avg=Avg("rating")).group_by("author_id").values("author_id", "avg")
        )

        for item in ret:
            author_id = item.get("author_id")
            avg = item.get("avg")
            if author_id == self.a1.pk:
                self.assertEqual(avg, 4.5)
            elif author_id == self.a2.pk:
                self.assertEqual(avg, 2.0)

    async def test_avg_group_by_with_join(self):
        ret = (
            await Book.annotate(avg=Avg("rating"))
            .group_by("author__name")
            .values("author__name", "avg")
        )
        self.assertListSortEqual(
            ret,
            [{"author__name": "author1", "avg": 4.5}, {"author__name": "author2", "avg": 2}],
            sorted_key="author__name",
        )

    async def test_avg_filter_group_by(self):
        ret = (
            await Book.annotate(avg=Avg("rating"))
            .filter(avg__gt=3)
            .group_by("author_id")
            .values_list("author_id", "avg")
        )
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0][1], 4.5)

    async def test_count_values_list_group_by(self):
        ret = (
            await Book.annotate(count=Count("id"))
            .group_by("author_id")
            .values_list("author_id", "count")
        )

        for item in ret:
            author_id = item[0]
            count = item[1]
            if author_id == self.a1.pk:
                self.assertEqual(count, 10)
            elif author_id == self.a2.pk:
                self.assertEqual(count, 5)

    async def test_count_values_list_group_by_with_join(self):
        ret = (
            await Book.annotate(count=Count("id"))
            .group_by("author__name")
            .values_list("author__name", "count")
        )
        self.assertListSortEqual(ret, [("author1", 10), ("author2", 5)])

    async def test_count_values_list_filter_group_by(self):
        ret = (
            await Book.annotate(count=Count("id"))
            .filter(count__gt=6)
            .group_by("author_id")
            .values_list("author_id", "count")
        )
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0][1], 10)

    async def test_sum_values_list_group_by(self):
        ret = (
            await Book.annotate(sum=Sum("rating"))
            .group_by("author_id")
            .values_list("author_id", "sum")
        )
        for item in ret:
            author_id = item[0]
            sum_ = item[1]
            if author_id == self.a1.pk:
                self.assertEqual(sum_, 45.0)
            elif author_id == self.a2.pk:
                self.assertEqual(sum_, 10.0)

    async def test_sum_values_list_group_by_with_join(self):
        ret = (
            await Book.annotate(sum=Sum("rating"))
            .group_by("author__name")
            .values_list("author__name", "sum")
        )
        self.assertListSortEqual(ret, [("author1", 45.0), ("author2", 10.0)])

    async def test_sum_values_list_filter_group_by(self):
        ret = (
            await Book.annotate(sum=Sum("rating"))
            .filter(sum__gt=11)
            .group_by("author_id")
            .values_list("author_id", "sum")
        )
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0][1], 45.0)

    async def test_avg_values_list_group_by(self):
        ret = (
            await Book.annotate(avg=Avg("rating"))
            .group_by("author_id")
            .values_list("author_id", "avg")
        )

        for item in ret:
            author_id = item[0]
            avg = item[1]
            if author_id == self.a1.pk:
                self.assertEqual(avg, 4.5)
            elif author_id == self.a2.pk:
                self.assertEqual(avg, 2.0)

    async def test_avg_values_list_group_by_with_join(self):
        ret = (
            await Book.annotate(avg=Avg("rating"))
            .group_by("author__name")
            .values_list("author__name", "avg")
        )
        self.assertListSortEqual(ret, [("author1", 4.5), ("author2", 2.0)])

    async def test_avg_values_list_filter_group_by(self):
        ret = (
            await Book.annotate(avg=Avg("rating"))
            .filter(avg__gt=3)
            .group_by("author_id")
            .values_list("author_id", "avg")
        )
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0][1], 4.5)

    async def test_implicit_group_by(self):
        ret = await Author.annotate(count=Count("books")).filter(count__gt=6)
        self.assertEqual(ret[0].count, 10)

    async def test_group_by_annotate_result(self):
        ret = (
            await Book.annotate(upper_name=Upper("author__name"), count=Count("id"))
            .group_by("upper_name")
            .values("upper_name", "count")
        )
        self.assertListSortEqual(
            ret,
            [{"upper_name": "AUTHOR1", "count": 10}, {"upper_name": "AUTHOR2", "count": 5}],
            sorted_key="upper_name",
        )

    async def test_group_by_requiring_nested_joins(self):
        tournament_first = await Tournament.create(name="Tournament 1", desc="d1")
        tournament_second = await Tournament.create(name="Tournament 2", desc="d2")

        event_first = await Event.create(name="1", tournament=tournament_first)
        event_second = await Event.create(name="2", tournament=tournament_first)
        event_third = await Event.create(name="3", tournament=tournament_second)

        team_first = await Team.create(name="First", alias=2)
        team_second = await Team.create(name="Second", alias=4)
        team_third = await Team.create(name="Third", alias=5)

        await team_first.events.add(event_first)
        await team_second.events.add(event_second)
        await team_third.events.add(event_third)

        ret = (
            await Tournament.annotate(avg=Avg("events__participants__alias"))
            .group_by("desc")
            .order_by("desc")
            .values("desc", "avg")
        )
        self.assertEqual(ret, [{"avg": 3, "desc": "d1"}, {"avg": 5, "desc": "d2"}])

    async def test_group_by_ambigious_column(self):
        tournament_first = await Tournament.create(name="Tournament 1")
        tournament_second = await Tournament.create(name="Tournament 2")

        await Event.create(name="1", tournament=tournament_first)
        await Event.create(name="2", tournament=tournament_first)
        await Event.create(name="3", tournament=tournament_second)

        base_query = (
            Tournament.annotate(event_count=Count("events")).group_by("name").order_by("name")
        )
        ret = await base_query.values("name", "event_count")
        self.assertEqual(
            ret,
            [
                {"event_count": 2, "name": "Tournament 1"},
                {"event_count": 1, "name": "Tournament 2"},
            ],
        )

        ret = await base_query.values_list("name", "event_count")
        self.assertEqual(
            ret,
            [("Tournament 1", 2), ("Tournament 2", 1)],
        )

    async def test_group_by_nested_column(self):
        tournament_first = await Tournament.create(name="A")
        tournament_second = await Tournament.create(name="B")

        await Event.create(name="1", tournament=tournament_first)
        await Event.create(name="2", tournament=tournament_first)
        await Event.create(name="3", tournament=tournament_first)
        await Event.create(name="4", tournament=tournament_second)

        base_query = (
            Event.annotate(count=Count("event_id"))
            .group_by("tournament__name")
            .order_by("-tournament__name")
        )
        ret = await base_query.values("tournament__name", "count")
        self.assertEqual(
            ret,
            [
                {"count": 1, "tournament__name": "B"},
                {"count": 3, "tournament__name": "A"},
            ],
        )

        ret = await base_query.values_list("tournament__name", "count")
        self.assertEqual(
            ret,
            [("B", 1), ("A", 3)],
        )

    async def test_group_by_id_with_nested_filter(self):
        ret = await Book.filter(author__name="author1").group_by("id").values_list("id")
        self.assertEqual(set(ret), {(book.id,) for book in self.books1})
