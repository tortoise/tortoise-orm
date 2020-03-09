=======
Roadmap
=======

Short-term
==========

Our short term goal is to ship the current implementation as MVP, just somewhat matured.

For ``v1.0`` that involves:

* Timezone support

Mid-term
========

Here we have all the features that is slightly further out, in no particular order:

* Performance work:
    * Sub queries
    * Change to all-parametrized queries
    * Faster MySQL driver (possibly based on mysqlclient)
    * Consider using Cython to accelerate critical loops

* Convenience/Ease-Of-Use work:
    * Make ``DELETE`` honour ``limit`` and ``offset``
    * ``.filter(field=None)`` to work as expected

* Expand in the ``init`` framework:
    * Ability to have Management Commands
    * Ability to define Management Commands
    * Make it simple to inspect Models and Management Commands without using private APIs.

* Migrations
    * Comprehensive schema Migrations
    * Automatic forward Migration building
    * Ability to easily run arbitrary code in a migration
    * Ability to get a the Models for that exact time of the migration, to ensure safe & consistent data migrations
    * Cross-DB support
    * Fixtures as a property of a migration

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
