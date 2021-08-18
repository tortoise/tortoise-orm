.. _example_blacksheep:

===================
BlackSheep Examples
===================

This is an example of the  :ref:`contrib_blacksheep`

**Usage:**

.. code-block:: sh

    uvicorn server:app --reload


.. rst-class:: emphasize-children

Basic non-relational example
============================

models.py
---------
.. literalinclude::  ../../examples/blacksheep/models.py

test_api.py
--------
.. literalinclude::  ../../examples/blacksheep/test_api.py

server.py
-------
.. literalinclude::  ../../examples/blacksheep/server.py
