import re

import pytest

from tests.testmodels import CharPkModel, Event, IntFields
from tortoise import connections
from tortoise.backends.psycopg.client import PsycopgClient
from tortoise.expressions import F
from tortoise.functions import Coalesce, Concat


@pytest.fixture
def sql_context(db):
    """Fixture providing database connection, dialect and psycopg flag."""
    db_conn = connections.get("models")
    dialect = db_conn.schema_generator.DIALECT
    is_psycopg = isinstance(db_conn, PsycopgClient)
    return db_conn, dialect, is_psycopg


def test_filter(sql_context):
    db, dialect, is_psycopg = sql_context
    sql = CharPkModel.all().filter(id="123").sql()
    if dialect == "mysql":
        expected = "SELECT `id` FROM `charpkmodel` WHERE `id`=%s"
    elif dialect == "postgres":
        if is_psycopg:
            expected = 'SELECT "id" FROM "charpkmodel" WHERE "id"=%s'
        else:
            expected = 'SELECT "id" FROM "charpkmodel" WHERE "id"=$1'
    else:
        expected = 'SELECT "id" FROM "charpkmodel" WHERE "id"=?'

    assert sql == expected


def test_filter_with_limit_offset(sql_context):
    db, dialect, is_psycopg = sql_context
    sql = CharPkModel.all().filter(id="123").limit(10).offset(0).sql()
    if dialect == "mysql":
        expected = "SELECT `id` FROM `charpkmodel` WHERE `id`=%s LIMIT %s OFFSET %s"
    elif dialect == "postgres":
        if is_psycopg:
            expected = 'SELECT "id" FROM "charpkmodel" WHERE "id"=%s LIMIT %s OFFSET %s'
        else:
            expected = 'SELECT "id" FROM "charpkmodel" WHERE "id"=$1 LIMIT $2 OFFSET $3'
    elif dialect == "mssql":
        expected = 'SELECT "id" FROM "charpkmodel" WHERE "id"=? ORDER BY (SELECT 0) OFFSET ? ROWS FETCH NEXT ? ROWS ONLY'
    else:
        expected = 'SELECT "id" FROM "charpkmodel" WHERE "id"=? LIMIT ? OFFSET ?'

    assert sql == expected


def test_group_by(sql_context):
    db, dialect, is_psycopg = sql_context
    sql = IntFields.all().group_by("intnum").values("intnum").sql()
    if dialect == "mysql":
        expected = "SELECT `intnum` `intnum` FROM `intfields` GROUP BY `intnum`"
    else:
        expected = 'SELECT "intnum" "intnum" FROM "intfields" GROUP BY "intnum"'
    assert sql == expected


def test_annotate(sql_context):
    db, dialect, is_psycopg = sql_context
    sql = CharPkModel.all().annotate(id_plus_one=Concat(F("id"), "_postfix")).sql()
    if dialect == "mysql":
        expected = "SELECT `id`,CONCAT(`id`,%s) `id_plus_one` FROM `charpkmodel`"
    elif dialect == "postgres":
        if is_psycopg:
            expected = 'SELECT "id",CONCAT("id"::text,%s::text) "id_plus_one" FROM "charpkmodel"'
        else:
            expected = 'SELECT "id",CONCAT("id"::text,$1::text) "id_plus_one" FROM "charpkmodel"'
    else:
        expected = 'SELECT "id",CONCAT("id",?) "id_plus_one" FROM "charpkmodel"'
    assert sql == expected


def test_annotate_concat_fields(sql_context):
    db, dialect, is_psycopg = sql_context
    sql = CharPkModel.all().annotate(id_double=Concat(F("id"), F("id"))).sql()
    if dialect == "mysql":
        expected = "SELECT `id`,CONCAT(`id`,`id`) `id_double` FROM `charpkmodel`"
    elif dialect == "postgres":
        expected = 'SELECT "id",CONCAT("id"::text,"id"::text) "id_double" FROM "charpkmodel"'
    else:
        expected = 'SELECT "id",CONCAT("id","id") "id_double" FROM "charpkmodel"'
    assert sql == expected


def test_annotate_coalesce_field_expression(sql_context):
    db, dialect, is_psycopg = sql_context
    sql = IntFields.all().annotate(num=Coalesce("intnum", F("intnum_null"))).values("num").sql()
    if dialect == "mysql":
        expected = "SELECT COALESCE(`intnum`,`intnum_null`) `num` FROM `intfields`"
    elif dialect == "postgres":
        expected = 'SELECT COALESCE("intnum","intnum_null") "num" FROM "intfields"'
    else:
        expected = 'SELECT COALESCE("intnum","intnum_null") "num" FROM "intfields"'
    assert sql == expected


def test_annotate_function_join_expression(sql_context):
    db, dialect, is_psycopg = sql_context
    qset = Event.all().annotate(full_name=Concat("name", F("tournament__name"))).values("full_name")
    sql = qset.sql()
    join_match = (
        r'LEFT OUTER JOIN [`"]tournament[`"] [`"]event__tournament[`"] ON '
        r'[`"]event__tournament[`"]\.[`"]id[`"]=[`"]event[`"]\.[`"]tournament_id[`"]'
    )
    assert re.search(join_match, sql)
    concat_match = (
        r"CONCAT\(`?event`?\.`?name`?(?:::text)?\s*,\s*`?event__tournament`?\.`?name`?"
        r"(?:::text)?\)"
        r'|CONCAT\("event"\."name"(?:::text)?\s*,\s*"event__tournament"\."name"'
        r"(?:::text)?\)"
    )
    assert re.search(concat_match, sql)


def test_values(sql_context):
    db, dialect, is_psycopg = sql_context
    sql = IntFields.filter(intnum=1).values("intnum").sql()
    if dialect == "mysql":
        expected = "SELECT `intnum` `intnum` FROM `intfields` WHERE `intnum`=%s"
    elif dialect == "postgres":
        if is_psycopg:
            expected = 'SELECT "intnum" "intnum" FROM "intfields" WHERE "intnum"=%s'
        else:
            expected = 'SELECT "intnum" "intnum" FROM "intfields" WHERE "intnum"=$1'
    else:
        expected = 'SELECT "intnum" "intnum" FROM "intfields" WHERE "intnum"=?'
    assert sql == expected


def test_values_list(sql_context):
    db, dialect, is_psycopg = sql_context
    sql = IntFields.filter(intnum=1).values_list("intnum").sql()
    if dialect == "mysql":
        expected = "SELECT `intnum` `0` FROM `intfields` WHERE `intnum`=%s"
    elif dialect == "postgres":
        if is_psycopg:
            expected = 'SELECT "intnum" "0" FROM "intfields" WHERE "intnum"=%s'
        else:
            expected = 'SELECT "intnum" "0" FROM "intfields" WHERE "intnum"=$1'
    else:
        expected = 'SELECT "intnum" "0" FROM "intfields" WHERE "intnum"=?'
    assert sql == expected


def test_exists(sql_context):
    db, dialect, is_psycopg = sql_context
    sql = IntFields.filter(intnum=1).exists().sql()
    if dialect == "mysql":
        expected = "SELECT 1 FROM `intfields` WHERE `intnum`=%s LIMIT %s"
    elif dialect == "postgres":
        if is_psycopg:
            expected = 'SELECT 1 FROM "intfields" WHERE "intnum"=%s LIMIT %s'
        else:
            expected = 'SELECT 1 FROM "intfields" WHERE "intnum"=$1 LIMIT $2'
    elif dialect == "mssql":
        expected = 'SELECT 1 FROM "intfields" WHERE "intnum"=? ORDER BY (SELECT 0) OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY'
    else:
        expected = 'SELECT 1 FROM "intfields" WHERE "intnum"=? LIMIT ?'
    assert sql == expected


def test_count(sql_context):
    db, dialect, is_psycopg = sql_context
    sql = IntFields.all().filter(intnum=1).count().sql()
    if dialect == "mysql":
        expected = "SELECT COUNT(*) FROM `intfields` WHERE `intnum`=%s"
    elif dialect == "postgres":
        if is_psycopg:
            expected = 'SELECT COUNT(*) FROM "intfields" WHERE "intnum"=%s'
        else:
            expected = 'SELECT COUNT(*) FROM "intfields" WHERE "intnum"=$1'
    else:
        expected = 'SELECT COUNT(*) FROM "intfields" WHERE "intnum"=?'
    assert sql == expected


def test_update(sql_context):
    db, dialect, is_psycopg = sql_context
    sql = IntFields.filter(intnum=2).update(intnum=1).sql()
    if dialect == "mysql":
        expected = "UPDATE `intfields` SET `intnum`=%s WHERE `intnum`=%s"
    elif dialect == "postgres":
        if is_psycopg:
            expected = 'UPDATE "intfields" SET "intnum"=%s WHERE "intnum"=%s'
        else:
            expected = 'UPDATE "intfields" SET "intnum"=$1 WHERE "intnum"=$2'
    else:
        expected = 'UPDATE "intfields" SET "intnum"=? WHERE "intnum"=?'
    assert sql == expected


def test_delete(sql_context):
    db, dialect, is_psycopg = sql_context
    sql = IntFields.filter(intnum=2).delete().sql()
    if dialect == "mysql":
        expected = "DELETE FROM `intfields` WHERE `intnum`=%s"
    elif dialect == "postgres":
        if is_psycopg:
            expected = 'DELETE FROM "intfields" WHERE "intnum"=%s'
        else:
            expected = 'DELETE FROM "intfields" WHERE "intnum"=$1'
    else:
        expected = 'DELETE FROM "intfields" WHERE "intnum"=?'
    assert sql == expected


@pytest.mark.asyncio
async def test_bulk_update(sql_context):
    db, dialect, is_psycopg = sql_context
    obj1 = await IntFields.create(intnum=1)
    obj2 = await IntFields.create(intnum=2)
    obj1.intnum = obj1.intnum + 1
    obj2.intnum = obj2.intnum + 1
    sql = IntFields.bulk_update([obj1, obj2], fields=["intnum"]).sql()

    if dialect == "mysql":
        expected = "UPDATE `intfields` SET `intnum`=CASE WHEN `id`=%s THEN %s WHEN `id`=%s THEN %s END WHERE `id` IN (%s,%s)"
    elif dialect == "postgres":
        if is_psycopg:
            expected = 'UPDATE "intfields" SET "intnum"=CASE WHEN "id"=%s THEN CAST(%s AS INT) WHEN "id"=%s THEN CAST(%s AS INT) END WHERE "id" IN (%s,%s)'
        else:
            expected = 'UPDATE "intfields" SET "intnum"=CASE WHEN "id"=$1 THEN CAST($2 AS INT) WHEN "id"=$3 THEN CAST($4 AS INT) END WHERE "id" IN ($5,$6)'
    else:
        expected = 'UPDATE "intfields" SET "intnum"=CASE WHEN "id"=? THEN ? WHEN "id"=? THEN ? END WHERE "id" IN (?,?)'
    assert sql == expected


@pytest.mark.asyncio
async def test_bulk_create_autogenerated_pk(sql_context):
    db, dialect, is_psycopg = sql_context
    sql = IntFields.bulk_create(
        [IntFields(intnum=1, intnum_null=2), IntFields(intnum=3, intnum_null=4)]
    ).sql()
    if dialect == "mysql":
        expected = "INSERT INTO `intfields` (`intnum`,`intnum_null`) VALUES (%s,%s)"
    elif dialect == "postgres":
        if is_psycopg:
            expected = (
                'INSERT INTO "intfields" ("intnum","intnum_null") VALUES (%s,%s) RETURNING "id"'
            )
        else:
            expected = (
                'INSERT INTO "intfields" ("intnum","intnum_null") VALUES ($1,$2) RETURNING "id"'
            )
    else:
        expected = 'INSERT INTO "intfields" ("intnum","intnum_null") VALUES (?,?)'
    assert sql == expected


@pytest.mark.asyncio
async def test_bulk_create_specified_pk(sql_context):
    db, dialect, is_psycopg = sql_context
    sql = IntFields.bulk_create([IntFields(id=1, intnum=1), IntFields(id=2, intnum=2)]).sql()
    if dialect == "mysql":
        expected = "INSERT INTO `intfields` (`id`,`intnum`,`intnum_null`) VALUES (%s,%s,%s)"
    elif dialect == "postgres":
        if is_psycopg:
            expected = 'INSERT INTO "intfields" ("id","intnum","intnum_null") VALUES (%s,%s,%s)'
        else:
            expected = 'INSERT INTO "intfields" ("id","intnum","intnum_null") VALUES ($1,$2,$3)'
    else:
        expected = 'INSERT INTO "intfields" ("id","intnum","intnum_null") VALUES (?,?,?)'
    assert sql == expected
