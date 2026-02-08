=======
Roadmap
=======

Mid-term
========

Here we have all the features that is slightly further out, in no particular order:

* Performance work:
    * [done] Sub queries
    * [done] Change to all-parametrized queries
    * Faster MySQL driver (possibly based on mysqlclient)
    * Consider using Cython to accelerate critical loops

* Convenience/Ease-Of-Use work:
    * Make ``DELETE`` honour ``limit`` and ``offset``
    * [done] ``.filter(field=None)`` to work as expected

* Expand in the ``init`` framework:
    * Ability to have Management Commands
    * Ability to define Management Commands
    * Make it simple to inspect Models and Management Commands without using private APIs.

* Migrations
    * Built-in migrations shipped (schema, autodetector, CLI, data migrations).
    * Follow-ups: optimization/merging tools, fixture support, expanded docs/examples.

* Serialization support
    * Add deserialization support
    * Make default serializers support some validation
    * Provide clean way to replace serializers with custom solution

* Extra DB support
    * CockroachDB
    * Firebird

* Enhanced test support
    * ``hypothesis`` strategy builder

* Fields
    * Expand on standard provided fields

* Documentation
    * Tutorials

Long-term
=========

Become the de facto Python AsyncIO ORM.
