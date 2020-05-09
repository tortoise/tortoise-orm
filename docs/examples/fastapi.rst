.. _example_fastapi:

================
FastAPI Examples
================

This is an example of the  :ref:`contrib_fastapi`

**Usage:**

.. code-block:: sh

    uvicorn main:app --reload


.. rst-class:: emphasize-children

Basic non-relational example
============================

models.py
---------
.. literalinclude::  ../../examples/fastapi/models.py

tests.py
-------
.. literalinclude::  ../../examples/fastapi/_tests.py
main.py
-------
.. literalinclude::  ../../examples/fastapi/main.py
