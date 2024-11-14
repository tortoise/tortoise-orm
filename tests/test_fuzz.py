from tests.testmodels import CharFields
from tortoise.contrib import test
from tortoise.contrib.test.condition import NotEQ
from tortoise.functions import Upper

DODGY_STRINGS = [
    "a/",
    "a\\",
    "a\\'",
    "a\\x39",
    "a'",
    '"',
    '""',
    "'",
    "''",
    "\\_",
    "\\\\_",
    "‘a",
    "a’",
    "‘a’",
    "a/a",
    "a\\a",
    "0x39",
    "%a%",
    "_a_",
    "WC[R]S123456",
    "\x00",
    "a\x00b",
    "'\x00'",
    "\\\x00\\",
    "\x01!\U00043198",
    "\x02\U0006501c",
    "\x03㊿\U000e90ff\U0007d718\x16'%\U000b712a(\x16",
    "\x03\U000d435e\U000aa4cb)\U000fe59b",
    "\x05\x10\U0009417f\U000f22e3\U000a5932🔈\U000a5e47\x18\U0006c16b\x05",
    "\nꝢ$\x17\r\x17\U00014dc2嵋0\U0010fda8\U00041dfa",
    "\x0c\U000d4858",
    "\r",
    '\r\r\U0006c50e\U000e309aᕫ%"\U00105213\U0007ba4b\x03\x0c',
    "\rꝢ$\x17\r\x17\U00014dc2嵋0\U0010fda8\U00041dfa",
    "\x0e\x0e",
    "\x0f\uf308𡉙\x1f\U0008ceaf\x19\U000f156b(\U0006c5b0\U0003881c\U0004b76a\U0010b7a2*+\x1b\x19$\U000f643f,(\U000b7e06",
    "\x14\x14",
    "\x14\U000b45e4.\x19\x01,\U00058aa5\U0008da94\U000bb53e\x10\U000a0328%\U0008e967",
    "\x14\U000eb331",
    "\x17\x17%\x12\U0008c069\x18\x10(\x1f\x0f",
    "\x17\x17(\U0008c069\x18\x10(\x1f\x0f",
    "\x17\x17\U000a084e\U0008c069\x18\x10(\x1f\x0f",
    "\x17((\U0008c069\x18\x10(\x1f\x0f",
    "\x17\U0006083e\x18",
    "\x17\U000ef05e%\x12\U0008c069\x18\x10(\x1f\x0f",
    '\x17\U00108f29\x18\x1c"\x18',
    "\x19\x19\x19",
    "\x19\x19-",
    "\x19\x19-\U000a0865",
    "\x1b",
    "\x1b\x19-\U000a0865",
    '\x1d\x19+\x1c㈏\U000b0305\U000ffbf2\x1b+\U000ff7bf"\U000557c3\x1c%\n',
    '\x1d\x19+\x1c\U000ff7bf\U000b0305\U000ffbf2\x1b+\U000ff7bf"\U000557c3\x1c%\n',
    '\x1d\x19㈏\x1c㈏\U000b0305\U000ffbf2\x1b+\U000ff7bf"\U000557c3\x1c%\n',
    '\x1d\x19㈏\x1c\U000566bf\U000b0305\U000ffbf2\x1b+\U000ff7bf"\U000557c3\x1c%\n',
    "\x1d\U0005f530",
    "\x1f",
    "\x1f\x18",
    "\x1f\x1f🔈",
    "\x1f\x1f🔈\x1f\U000a5932🔈\U000a5e47\x18\U0006c16b\x05",
    "\x1f\x1f🔈\U000f22e3\U000a5932🔈\U000a5e47\x18\U0006c16b\x05",
    "\x1f\uf308𡉙\x1f\U0008ceaf\x19\U000f156b(\U0006c5b0\U0003881c\U0004b76a\U0010b7a2*+\x1b\x19$\U000f643f,(\U000b7e06",
    "\x1f𛉅\U001086b3\x0b\x1b\U00077711\U00057223\U0005e650婯\x1d0\U000c0272\x02\x15\U000d159c\U0005997e!\x04&\x04",
    "\x1f\U00077711\U001086b3\x0b\x1b\U00077711\U00057223\U0005e650婯\x1d0\U000c0272\x02\x15\U000d159c\U0005997e!\x04&\x04",
    "\x1f\U000a0850\U0009417f\U000f22e3\U000a5932🔈\U000a5e47\x18\U0006c16b\x05",
    "%\U000e6f0c",
    "&",
    "(((\U0008c069\x18\x10(\x1f\x0f",
    "*\x10'\U0001ea89\U0006a5fe\U00097b9b\x1e",
    "+/",
    "/𬍘&\U00059587+\n\U0003a4ef\x06\U0004675f\x12\U000bfa73\x14\x02(",
    "0",
    "滕'\u16faꮭ\U00041a44\U000d04ba\U000d341c\n'$,\U000bac0b\U000446f8\U000ff86e(",
    "𩣂𩣂\uf580\U000508c8𩣂\U00041150\uf580\x1c",
    "𩣂\U0005215e\uf580\U000508c8𩣂\U00041150\uf580\x1c",
    "\U0003b0da",
    "\U0003ffe5*\n\U000f9326,",
    "\U00050c3e''",
    "\U00050c3e'\U00050c3e",
    "\U0005215e",
    "\U0005215e\U0005215e\x18\U000508c8𩣂\U00041150\uf580\x1c",
    "\U0005215e\U0005215e\uf580\U000508c8𩣂\U00041150\uf580\x1c",
    "\U00059504\U000a33bc\x18\x1f\U000b3017\U000643a3\x18\U000ea429\U000af53c!\U000bcc8f\U000606df",
    "\U0005b823\U0007d224",
    "\U0007bf54\U0001e97a\x08\x18\x04\x06\U000c4329淪",
    "\U0008d96d\x02\U0006d816",
    "\U0009601b\U000b210a\U00058370",
    "\U000965f7'",
    "\U000965f7'\U00050c3e",
    "\U000a9760\U00108859\x0c\r\U00019fbb\U00045885靜$!\U00074df5\x1a\U000c9c7d\U0004bb28\x08\x19\U00099df6+\x1c!\U0003d75f\U0003f457\U0001352e/\U000495db\U000b6234(",
    "\U000aee91\x1c\x1f\U0001cac6\x08\x1d",
    "\U000af7bd\x17",
    "\U000e6f0c\U000e6f0c",
    "\U000f01c8\x0e",
]


class TestFuzz(test.TestCase):
    @test.requireCapability(dialect=NotEQ("mssql"))
    async def test_char_fuzz(self):
        for char in DODGY_STRINGS:
            # print(repr(char))
            if "\x00" in char and self._db.capabilities.dialect in ["postgres"]:
                # PostgreSQL doesn't support null values as text. Ever. So skip these.
                continue

            # Create
            obj1 = await CharFields.create(char=char)

            # Get-by-pk, and confirm that reading is correct
            obj2 = await CharFields.get(pk=obj1.pk)
            self.assertEqual(char, obj2.char)

            # Update data using a queryset, confirm that update is correct
            await CharFields.filter(pk=obj1.pk).update(char="a")
            await CharFields.filter(pk=obj1.pk).update(char=char)
            obj3 = await CharFields.get(pk=obj1.pk)
            self.assertEqual(char, obj3.char)

            # Filter by value in queryset, and confirm that it fetched the right one
            obj4 = await CharFields.get(pk=obj1.pk, char=char)
            self.assertEqual(obj1.pk, obj4.pk)
            self.assertEqual(char, obj4.char)

            # LIKE statements are not strict, so require all of these to match
            obj5 = await CharFields.get(
                pk=obj1.pk,
                char__startswith=char,
                char__endswith=char,
                char__contains=char,
                char__istartswith=char,
                char__iendswith=char,
                char__icontains=char,
            )
            self.assertEqual(obj1.pk, obj5.pk)
            self.assertEqual(char, obj5.char)

            # Filter by a function
            obj6 = (
                await CharFields.annotate(upper_char=Upper("char"))
                .filter(id=obj1.pk, upper_char=Upper("char"))
                .first()
            )
            self.assertEqual(obj1.pk, obj6.pk)
            self.assertEqual(char, obj6.char)
