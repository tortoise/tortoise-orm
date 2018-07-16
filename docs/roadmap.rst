=======
Roadmap
=======

Short-term
==========

Our short term goal is to ship the current implementation as MVP, just somewhat matured.

For ``v1.0`` that involves:

* Comprehensive test suite
* Clear and concise examples
* Refactored ``init`` framework
* Refactored Fields Schema generation
* Add MySQL support


Mid-term
========

Here we have all the features that is sligtly further our:

* Performance work:
    * Subqueries
    * Benchmark suite
    * Bulk operations
    * Minimising overhead of building query set
    * Minimising overhead of creating objects
    * ...

* Convenience/Ease-Of-Use work:
    * Make ``DELETE`` honour ``limit`` and ``offset``
    * ``.filter(field=None)`` to work as expected

* Expand in the ``init`` framework:
    * Ability to have Management Commands
    * Ability to define Management Commands
    * Make it simple to control ``init`` from another system
    * Make it simple to inspect Models and Management Commands without using private APIs.

* Better Aggregate functions
    * Make it easier to do simple aggregations
    * Expand annotation framework to add statistical functions

* Atomicity framework
    * Simpler ``with atomic`` blocks to manage isolation
    * Ability to set ACID conformance expectations

* Migrations
    * Comprehensive schema in Migrations
    * Automatic forward Migration building
    * Ability to easily run arb code in a migration
    * Ability to get a the Models for that exact time of the migration, to ensure safe & consistent data migrations
    * Cross-DB support

* Serialisation support
    * Take inspiration from ``attrs`` and ``marshmallow``
    * Provide sane default serialisers that will work as-is for CRUD
    * Provide sane default schema generators
    * Make default serialisers support some validation
    * Make default serialisers support data conversion
    * Make default serialisers somewhat customiseable
    * Provide clean way to replace serialisers with custom solution
    * Define strategy to work with ``ManyToMany`` relationships

* Enhanced test support
    * Better performance for test runner
      (use atomicity/snapshots instead of always rebuilding database)
    * ``hypothesis`` strategy builer

* Fields
    * Expand on standard provided fields
    * Provide a simple way to add custom field types
    * Provide a simple way of overriding fields on a per-database case
      (for either performance or functionality)

* Documentation
    * Tutorials

Long-term
=========

Become the de-facto Python asyncio ORM.
