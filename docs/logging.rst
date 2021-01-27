=======
Logging
=======

Current tortoise has two loggers, `db_client` and `tortoise`.

`db_client` logging the information about execute query, and `tortoise` logging the information about runtime.

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
    logger_db_client = logging.getLogger("db_client")
    logger_db_client.setLevel(logging.DEBUG)
    logger_db_client.addHandler(sh)

    logger_tortoise = logging.getLogger("tortoise")
    logger_tortoise.setLevel(logging.DEBUG)
    logger_tortoise.addHandler(sh)

