import unittest

from pypika import MySQLQuery, Table


class InsertTests(unittest.TestCase):
    table_abc = Table("abc")

    def test_insert_ignore(self):
        q = MySQLQuery.into("abc").insert((1, "a", True)).on_conflict().do_nothing()
        self.assertEqual("INSERT IGNORE INTO `abc` VALUES (1,'a',true)", str(q))

    def test_upsert(self):
        q = (
            MySQLQuery.into("abc")
            .insert(1, "b", False)
            .as_("aaa")
            .on_conflict(self.table_abc.id)
            .do_update("abc")
        )
        self.assertEqual(
            "INSERT INTO `abc` VALUES (1,'b',false) AS `aaa` ON DUPLICATE KEY UPDATE `abc`=`aaa`.`abc`",
            str(q),
        )


class SelectTests(unittest.TestCase):
    table_abc = Table("abc")

    def test_normal_select(self):
        q = MySQLQuery.from_("abc").select("def")

        self.assertEqual("SELECT `def` FROM `abc`", str(q))

    def test_distinct_select(self):
        q = MySQLQuery.from_("abc").select("def").distinct()

        self.assertEqual("SELECT DISTINCT `def` FROM `abc`", str(q))

    def test_modifier_select(self):
        q = MySQLQuery.from_("abc").select("def").select("ghi").modifier("SQL_CALC_FOUND_ROWS")

        self.assertEqual("SELECT SQL_CALC_FOUND_ROWS `def`,`ghi` FROM `abc`", str(q))

    def test_multiple_modifier_select(self):
        q = (
            MySQLQuery.from_("abc")
            .select("def")
            .modifier("HIGH_PRIORITY")
            .modifier("SQL_CALC_FOUND_ROWS")
        )

        self.assertEqual("SELECT HIGH_PRIORITY SQL_CALC_FOUND_ROWS `def` FROM `abc`", str(q))


class UpdateTests(unittest.TestCase):
    table_abc = Table("abc")

    def test_update(self):
        q = MySQLQuery.into("abc").insert(1, [1, "a", True])

        self.assertEqual("INSERT INTO `abc` VALUES (1,[1,'a',true])", str(q))

    def test_on_duplicate_key_update_update(self):
        q = (
            MySQLQuery.into("abc")
            .insert(1, [1, "a", True])
            .on_conflict()
            .do_update(self.table_abc.a, "b")
        )

        self.assertEqual(
            "INSERT INTO `abc` VALUES (1,[1,'a',true]) ON DUPLICATE KEY UPDATE `a`='b'", str(q)
        )


class LoadCSVTests(unittest.TestCase):
    table_abc = Table("abc")

    def test_load_from_file(self):
        q1 = MySQLQuery.load("/path/to/file").into("abc")

        q2 = MySQLQuery.load("/path/to/file").into(self.table_abc)

        self.assertEqual(
            "LOAD DATA LOCAL INFILE '/path/to/file' INTO TABLE `abc` FIELDS TERMINATED BY ','",
            str(q1),
        )
        self.assertEqual(
            "LOAD DATA LOCAL INFILE '/path/to/file' INTO TABLE `abc` FIELDS TERMINATED BY ','",
            str(q2),
        )
