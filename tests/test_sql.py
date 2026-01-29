from tests.testmodels import CharPkModel, IntFields
from tortoise import connections
from tortoise.backends.psycopg.client import PsycopgClient
from tortoise.contrib import test
from tortoise.expressions import F
from tortoise.functions import Concat


class TestSQL(test.TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.db = connections.get("models")
        self.dialect = self.db.schema_generator.DIALECT
        self.is_psycopg = isinstance(self.db, PsycopgClient)

    def test_filter(self):
        sql = CharPkModel.all().filter(id="123").sql()
        if self.dialect == "mysql":
            expected = "SELECT `id` FROM `charpkmodel` WHERE `id`=%s"
        elif self.dialect == "postgres":
            if self.is_psycopg:
                expected = 'SELECT "id" FROM "charpkmodel" WHERE "id"=%s'
            else:
                expected = 'SELECT "id" FROM "charpkmodel" WHERE "id"=$1'
        else:
            expected = 'SELECT "id" FROM "charpkmodel" WHERE "id"=?'

        self.assertEqual(sql, expected)

    def test_filter_with_limit_offset(self):
        sql = CharPkModel.all().filter(id="123").limit(10).offset(0).sql()
        if self.dialect == "mysql":
            expected = "SELECT `id` FROM `charpkmodel` WHERE `id`=%s LIMIT %s OFFSET %s"
        elif self.dialect == "postgres":
            if self.is_psycopg:
                expected = 'SELECT "id" FROM "charpkmodel" WHERE "id"=%s LIMIT %s OFFSET %s'
            else:
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
            if self.is_psycopg:
                expected = (
                    'SELECT "id",CONCAT("id"::text,%s::text) "id_plus_one" FROM "charpkmodel"'
                )
            else:
                expected = (
                    'SELECT "id",CONCAT("id"::text,$1::text) "id_plus_one" FROM "charpkmodel"'
                )
        else:
            expected = 'SELECT "id",CONCAT("id",?) "id_plus_one" FROM "charpkmodel"'
        self.assertEqual(sql, expected)

    def test_values(self):
        sql = IntFields.filter(intnum=1).values("intnum").sql()
        if self.dialect == "mysql":
            expected = "SELECT `intnum` `intnum` FROM `intfields` WHERE `intnum`=%s"
        elif self.dialect == "postgres":
            if self.is_psycopg:
                expected = 'SELECT "intnum" "intnum" FROM "intfields" WHERE "intnum"=%s'
            else:
                expected = 'SELECT "intnum" "intnum" FROM "intfields" WHERE "intnum"=$1'
        else:
            expected = 'SELECT "intnum" "intnum" FROM "intfields" WHERE "intnum"=?'
        self.assertEqual(sql, expected)

    def test_values_list(self):
        sql = IntFields.filter(intnum=1).values_list("intnum").sql()
        if self.dialect == "mysql":
            expected = "SELECT `intnum` `0` FROM `intfields` WHERE `intnum`=%s"
        elif self.dialect == "postgres":
            if self.is_psycopg:
                expected = 'SELECT "intnum" "0" FROM "intfields" WHERE "intnum"=%s'
            else:
                expected = 'SELECT "intnum" "0" FROM "intfields" WHERE "intnum"=$1'
        else:
            expected = 'SELECT "intnum" "0" FROM "intfields" WHERE "intnum"=?'
        self.assertEqual(sql, expected)

    def test_exists(self):
        sql = IntFields.filter(intnum=1).exists().sql()
        if self.dialect == "mysql":
            expected = "SELECT 1 FROM `intfields` WHERE `intnum`=%s LIMIT %s"
        elif self.dialect == "postgres":
            if self.is_psycopg:
                expected = 'SELECT 1 FROM "intfields" WHERE "intnum"=%s LIMIT %s'
            else:
                expected = 'SELECT 1 FROM "intfields" WHERE "intnum"=$1 LIMIT $2'
        elif self.dialect == "mssql":
            expected = 'SELECT 1 FROM "intfields" WHERE "intnum"=? ORDER BY (SELECT 0) OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY'
        else:
            expected = 'SELECT 1 FROM "intfields" WHERE "intnum"=? LIMIT ?'
        self.assertEqual(sql, expected)

    def test_count(self):
        sql = IntFields.all().filter(intnum=1).count().sql()
        if self.dialect == "mysql":
            expected = "SELECT COUNT(*) FROM `intfields` WHERE `intnum`=%s"
        elif self.dialect == "postgres":
            if self.is_psycopg:
                expected = 'SELECT COUNT(*) FROM "intfields" WHERE "intnum"=%s'
            else:
                expected = 'SELECT COUNT(*) FROM "intfields" WHERE "intnum"=$1'
        else:
            expected = 'SELECT COUNT(*) FROM "intfields" WHERE "intnum"=?'
        self.assertEqual(sql, expected)

    def test_update(self):
        sql = IntFields.filter(intnum=2).update(intnum=1).sql()
        if self.dialect == "mysql":
            expected = "UPDATE `intfields` SET `intnum`=%s WHERE `intnum`=%s"
        elif self.dialect == "postgres":
            if self.is_psycopg:
                expected = 'UPDATE "intfields" SET "intnum"=%s WHERE "intnum"=%s'
            else:
                expected = 'UPDATE "intfields" SET "intnum"=$1 WHERE "intnum"=$2'
        else:
            expected = 'UPDATE "intfields" SET "intnum"=? WHERE "intnum"=?'
        self.assertEqual(sql, expected)

    def test_delete(self):
        sql = IntFields.filter(intnum=2).delete().sql()
        if self.dialect == "mysql":
            expected = "DELETE FROM `intfields` WHERE `intnum`=%s"
        elif self.dialect == "postgres":
            if self.is_psycopg:
                expected = 'DELETE FROM "intfields" WHERE "intnum"=%s'
            else:
                expected = 'DELETE FROM "intfields" WHERE "intnum"=$1'
        else:
            expected = 'DELETE FROM "intfields" WHERE "intnum"=?'
        self.assertEqual(sql, expected)

    async def test_bulk_update(self):
        obj1 = await IntFields.create(intnum=1)
        obj2 = await IntFields.create(intnum=2)
        obj1.intnum = obj1.intnum + 1
        obj2.intnum = obj2.intnum + 1
        sql = IntFields.bulk_update([obj1, obj2], fields=["intnum"]).sql()

        if self.dialect == "mysql":
            expected = "UPDATE `intfields` SET `intnum`=CASE WHEN `id`=%s THEN %s WHEN `id`=%s THEN %s END WHERE `id` IN (%s,%s)"
        elif self.dialect == "postgres":
            if self.is_psycopg:
                expected = 'UPDATE "intfields" SET "intnum"=CASE WHEN "id"=%s THEN CAST(%s AS INT) WHEN "id"=%s THEN CAST(%s AS INT) END WHERE "id" IN (%s,%s)'
            else:
                expected = 'UPDATE "intfields" SET "intnum"=CASE WHEN "id"=$1 THEN CAST($2 AS INT) WHEN "id"=$3 THEN CAST($4 AS INT) END WHERE "id" IN ($5,$6)'
        else:
            expected = 'UPDATE "intfields" SET "intnum"=CASE WHEN "id"=? THEN ? WHEN "id"=? THEN ? END WHERE "id" IN (?,?)'
        self.assertEqual(sql, expected)

    async def test_bulk_create_autogenerated_pk(self):
        sql = IntFields.bulk_create(
            [IntFields(intnum=1, intnum_null=2), IntFields(intnum=3, intnum_null=4)]
        ).sql()
        if self.dialect == "mysql":
            expected = "INSERT INTO `intfields` (`intnum`,`intnum_null`) VALUES (%s,%s)"
        elif self.dialect == "postgres":
            if self.is_psycopg:
                expected = (
                    'INSERT INTO "intfields" ("intnum","intnum_null") VALUES (%s,%s) RETURNING "id"'
                )
            else:
                expected = (
                    'INSERT INTO "intfields" ("intnum","intnum_null") VALUES ($1,$2) RETURNING "id"'
                )
        else:
            expected = 'INSERT INTO "intfields" ("intnum","intnum_null") VALUES (?,?)'
        self.assertEqual(sql, expected)

    async def test_bulk_create_specified_pk(self):
        sql = IntFields.bulk_create([IntFields(id=1, intnum=1), IntFields(id=2, intnum=2)]).sql()
        if self.dialect == "mysql":
            expected = "INSERT INTO `intfields` (`id`,`intnum`,`intnum_null`) VALUES (%s,%s,%s)"
        elif self.dialect == "postgres":
            if self.is_psycopg:
                expected = 'INSERT INTO "intfields" ("id","intnum","intnum_null") VALUES (%s,%s,%s)'
            else:
                expected = 'INSERT INTO "intfields" ("id","intnum","intnum_null") VALUES ($1,$2,$3)'
        else:
            expected = 'INSERT INTO "intfields" ("id","intnum","intnum_null") VALUES (?,?,?)'
        self.assertEqual(sql, expected)
