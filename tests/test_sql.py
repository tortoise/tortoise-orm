from tests.testmodels import CharPkModel, IntFields
from tortoise import connections
from tortoise.contrib import test
from tortoise.expressions import F
from tortoise.functions import Concat


class TestSQL(test.TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.db = connections.get("models")
        self.dialect = self.db.schema_generator.DIALECT

    def test_filter(self):
        sql = CharPkModel.all().filter(id="123").sql()
        if self.dialect == "mysql":
            expected = "SELECT `id` FROM `charpkmodel` WHERE `id`=%s"
        elif self.dialect == "postgres":
            expected = 'SELECT "id" FROM "charpkmodel" WHERE "id"=$1'
        else:
            expected = 'SELECT "id" FROM "charpkmodel" WHERE "id"=?'

        self.assertEqual(sql, expected)

    def test_filter_with_limit_offset(self):
        sql = CharPkModel.all().filter(id="123").limit(10).offset(0).sql()
        if self.dialect == "mysql":
            expected = "SELECT `id` FROM `charpkmodel` WHERE `id`=%s LIMIT %s OFFSET %s"
        elif self.dialect == "postgres":
            expected = 'SELECT "id" FROM "charpkmodel" WHERE "id"=$1 LIMIT $2 OFFSET $3'
        elif self.dialect == "mssql":
            expected = 'SELECT "id" FROM "charpkmodel" WHERE "id"=? ORDER BY (SELECT 0) OFFSET ? ROWS FETCH NEXT ? ROWS ONLY'
        else:
            expected = 'SELECT "id" FROM "charpkmodel" WHERE "id"=? LIMIT ? OFFSET ?'

        self.assertEqual(sql, expected)

    def test_group_by(self):
        sql = IntFields.all().group_by("intnum").values("intnum").sql()
        if self.dialect == "mysql":
            expected = "SELECT `intnum` `intnum` FROM `intfields` GROUP BY `intnum`"
        else:
            expected = 'SELECT "intnum" "intnum" FROM "intfields" GROUP BY "intnum"'
        self.assertEqual(sql, expected)

    def test_annotate(self):
        sql = CharPkModel.all().annotate(id_plus_one=Concat(F("id"), "_postfix")).sql()
        if self.dialect == "mysql":
            expected = "SELECT `id`,CONCAT(`id`,%s) `id_plus_one` FROM `charpkmodel`"
        elif self.dialect == "postgres":
            expected = 'SELECT "id",CONCAT("id",$1) "id_plus_one" FROM "charpkmodel"'
        else:
            expected = 'SELECT "id",CONCAT("id",?) "id_plus_one" FROM "charpkmodel"'
        self.assertEqual(sql, expected)

    def test_values(self):
        sql = IntFields.filter(intnum=1).values("intnum").sql()
        if self.dialect == "mysql":
            expected = "SELECT `intnum` `intnum` FROM `intfields` WHERE `intnum`=%s"
        elif self.dialect == "postgres":
            expected = 'SELECT "intnum" "intnum" FROM "intfields" WHERE "intnum"=$1'
        else:
            expected = 'SELECT "intnum" "intnum" FROM "intfields" WHERE "intnum"=?'
        self.assertEqual(sql, expected)

    def test_values_list(self):
        sql = IntFields.filter(intnum=1).values_list("intnum").sql()
        if self.dialect == "mysql":
            expected = "SELECT `intnum` `0` FROM `intfields` WHERE `intnum`=%s"
        elif self.dialect == "postgres":
            expected = 'SELECT "intnum" "0" FROM "intfields" WHERE "intnum"=$1'
        else:
            expected = 'SELECT "intnum" "0" FROM "intfields" WHERE "intnum"=?'
        self.assertEqual(sql, expected)

    def test_exists(self):
        sql = IntFields.filter(intnum=1).exists().sql()
        if self.dialect == "mysql":
            expected = "SELECT %s FROM `intfields` WHERE `intnum`=%s LIMIT %s"
        elif self.dialect == "postgres":
            expected = 'SELECT $1 FROM "intfields" WHERE "intnum"=$2 LIMIT $3'
        else:
            expected = 'SELECT ? FROM "intfields" WHERE "intnum"=? LIMIT ?'
        self.assertEqual(sql, expected)

    def test_count(self):
        sql = IntFields.all().filter(intnum=1).count().sql()
        if self.dialect == "mysql":
            expected = "SELECT COUNT(*) FROM `intfields` WHERE `intnum`=%s"
        elif self.dialect == "postgres":
            expected = 'SELECT COUNT(*) FROM "intfields" WHERE "intnum"=$1'
        else:
            expected = 'SELECT COUNT(*) FROM "intfields" WHERE "intnum"=?'
        self.assertEqual(sql, expected)

    @test.skip("Update queries are not parameterized yet")
    def test_update(self):
        sql = IntFields.filter(intnum=2).update(intnum=1).sql()
        if self.dialect == "mysql":
            expected = "UPDATE `intfields` SET `intnum`=%s WHERE `intnum`=%s"
        elif self.dialect == "postgres":
            expected = 'UPDATE "intfields" SET "intnum"=$1 WHERE "intnum"=$2'
        else:
            expected = 'UPDATE "intfields" SET "intnum"=? WHERE "intnum"=?'
        self.assertEqual(sql, expected)
