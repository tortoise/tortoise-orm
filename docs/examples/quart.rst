.. _example_quart:

=============
Quart Example
=============

This is an example of the :ref:`contrib_quart`

**Usage:**

.. code-block:: sh

    QUART_APP=main quart
        ...
        Commands:
          generate-schemas  Populate DB with Tortoise-ORM schemas.
          run               Start and run a development server.
          shell             Open a shell within the app context.

    # To generate schemas
    QUART_APP=main quart generate-schemas

    # To run
    QUART_APP=main quart run


models.py
=========
.. literalinclude::  ../../examples/quart/models.py

main.py
=======
.. literalinclude::  ../../examples/quart/main.py


