=======
Roadmap
=======

Short-term
==========

Our short term goal is to ship the current implementation as MVP, just somewhat matured.

For ``v1.0`` that involves:

* Comprehensive test suite
* Clear and concise examples
* Refactored Fields Schema generation
* Add MySQL support

Mid-term
========

Here we have all the features that is slightly further our:

* Performance work:
    * Sub queries
    * Benchmark suite
    * Bulk operations
    * Minimizing overhead of building query set
    * Minimizing overhead of creating objects
    * ...

* Convenience/Ease-Of-Use work:
    * Make ``DELETE`` honour ``limit`` and ``offset``
    * ``.filter(field=None)`` to work as expected
    * Enable the use of a primary key that is not ``IntField``
    * Enable to call the primary key something that isn't ``id``

* Expand in the ``init`` framework:
    * Ability to have Management Commands
    * Ability to define Management Commands
    * Make it simple to control ``init`` from another system
    * Make it simple to inspect Models and Management Commands without using private APIs.

* Better Aggregate functions
    * Make it easier to do simple aggregations
    * Expand annotation framework to add statistical functions

* Transaction framework
    * Ability to set ACID conformance expectations

* Migrations
    * Comprehensive schema in Migrations
    * Automatic forward Migration building
    * Ability to easily run arb code in a migration
    * Ability to get a the Models for that exact time of the migration, to ensure safe & consistent data migrations
    * Cross-DB support

* Serialization support
    * Take inspiration from ``attrs`` and ``marshmallow``
    * Provide sane default serializers that will work as-is for CRUD
    * Provide sane default schema generators
    * Make default serializers support some validation
    * Make default serializers support data conversion
    * Make default serializers somewhat customizable
    * Provide clean way to replace serializers with custom solution
    * Define strategy to work with ``ManyToMany`` relationships

* Enhanced test support
    * ``hypothesis`` strategy builder

* Fields
    * Expand on standard provided fields
    * Provide a simple way to add custom field types
    * Provide a simple way of overriding fields on a per-database case
      (for either performance or functionality)

* Documentation
    * Tutorials

Long-term
=========

Become the de facto Python AsyncIO ORM.
