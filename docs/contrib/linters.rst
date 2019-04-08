=======
Linters
=======

.. _pylint:

PyLint plugin
=============

Since Tortoise ORM uses MetaClasses to build the Model objects, PyLint will often not understand how the Models behave. We provided a `tortoise.pylint` plugin that enhances PyLints understanding of Models and Fields.

Usage
-----

In your projects ``.pylintrc`` file, ensure the following is set:

.. code-block:: ini

    load-plugins=tortoise.contrib.pylint


