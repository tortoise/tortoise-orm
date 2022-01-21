=======
Logging
=======

Current tortoise has two loggers, `tortoise.db_client` and `tortoise`.

`tortoise.db_client` logging the information about execute query, and `tortoise` logging the information about runtime.

If you want control the behavior of tortoise logging, such as print debug sql, you can configure it yourself like following.

.. code-block:: python3

    import logging

    fmt = logging.Formatter(
        fmt="%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(fmt)

    # will print debug sql
    logger_db_client = logging.getLogger("tortoise.db_client")
    logger_db_client.setLevel(logging.DEBUG)
    logger_db_client.addHandler(sh)

    logger_tortoise = logging.getLogger("tortoise")
    logger_tortoise.setLevel(logging.DEBUG)
    logger_tortoise.addHandler(sh)


You can also use your own formatter to add syntax coloration to sql, by using `pygments <https://pygments.org/>` :

.. code-block:: python3

    import logging

    from pygments import highlight
    from pygments.formatters.terminal import TerminalFormatter
    from pygments.lexers.sql import PostgresLexer

    postgres = PostgresLexer()
    terminal_formatter = TerminalFormatter()


    class PygmentsFormatter(logging.Formatter):
        def __init__(
            self,
            fmt="{asctime} - {name}:{lineno} - {levelname} - {message}",
            datefmt="%H:%M:%S",
        ):
            self.datefmt = datefmt
            self.fmt = fmt
            logging.Formatter.__init__(self, None, datefmt)

        def format(self, record: logging.LogRecord):
            """Format the logging record with slq's syntax coloration."""
            own_records = {
                attr: val
                for attr, val in record.__dict__.items()
                if not attr.startswith("_")
            }
            message = record.getMessage()
            name = record.name
            asctime = self.formatTime(record, self.datefmt)

            if name == "tortoise.db_client":
                if (
                    record.levelname == "DEBUG"
                    and not message.startswith("Created connection pool")
                    and not message.startswith("Closed connection pool")
                ):
                    message = highlight(message, postgres, terminal_formatter).rstrip()

            own_records.update(
                {
                    "message": message,
                    "name": name,
                    "asctime": asctime,
                }
            )

            return self.fmt.format(**own_records)



    # Then replace the formatter above by the following one
    fmt = PygmentsFormatter(
        fmt="{asctime} - {name}:{lineno} - {levelname} - {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
