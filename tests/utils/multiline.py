from textwrap import dedent


def multiline_code(s: str) -> str:
    """
    Normalize a multi-line code literal into a clean string constant.

    Strips the common leading whitespace shared by all non-blank lines
    (via :func:`textwrap.dedent`), then removes the single leading newline
    introduced by an opening triple quote. Leading blank lines do not
    affect the computed indent, and only one leading newline is removed.

    The caller's indentation around the literal is irrelevant: the result
    depends only on the content between the triple quotes, so the literal
    may be indented however the surrounding block requires.

    :param s: Raw multi-line string, usually a triple-quoted literal.
    :return: De-indented string with its single leading newline removed.

    Usage::

        code = multiline_code(
            '''
            from tortoise import Model, fields

            class Event(Model):
                name = fields.CharField(20)
            '''
        )
        # code == (
        #     "from tortoise import Model, fields\n"
        #     "\n"
        #     "class Event(Model):\n"
        #     "    name = fields.CharField(20)\n"
        # )
    """
    return dedent(s).removeprefix("\n")
