===========================
Tortoise Contribution Guide
===========================


Priorities
==========

An important part of Tortoise is that we want a simple interface, that only does what is expected.
As this is a value that is different for different people, we have settled on:

* Model/QuerySet usage should be explicit and concise.
* Keep it simple, as simple code not only often runs faster, but has less bugs too.
* Correctness > Ease-Of-Use > Performance > Maintenance
* Test everything. (Currently our test suite is not yet mature)
* Only do performance/memory optimisation when you have a repeatable benchmark to measure with.


Style
=====

Tortoise has set up style checkers as part of the CI pipeline,
but these don't pick up on the non-obvious style preferences.

Tortoise follows a the following agreed upon style:

* Keep to PEP8 where you can
* Max line-length is changed to 100
* Always try to separate out terms clearly rather than concatenate words directly:
    * ``some_purpose`` instead of ``somepurpose``
    * ``SomePurpose`` instead of ``Somepurpose``
* Keep in mind the targeted Python versions of ``>=3.5.3``:
    * Don't use f-strings
    * Stick to comment-style variable type annotations
