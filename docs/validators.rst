.. _validators:

==========
Validators
==========

A validator is a callable for model field that takes a value and raises a `ValidationError` if it doesn’t meet some criteria.

Usage
=====

You can pass a list of validators to `Field` parameter `validators`:

.. code-block:: python3

    class ValidatorModel(Model):
        regex = fields.CharField(max_length=100, null=True, validators=[RegexValidator("abc.+", re.I)])

    # oh no, this will raise ValidationError!
    await ValidatorModel.create(regex="ccc")
    # this is great!
    await ValidatorModel.create(regex="abcd")

Built-in Validators
===================

Here is the list of built-in validators:

.. automodule:: tortoise.validators
    :members:
    :undoc-members:

Custom Validator
================

There are two methods to write a custom validator, one you can write a function by passing a given value, another you can inherit `tortoise.validators.Validator` and implement `__call__`.

Here is a example to write a custom validator to validate the given value is an even number:

.. code-block:: python3

    from tortoise.validators import Validator
    from tortoise.exceptions import ValidationError

    class EvenNumberValidator(Validator):
        """
        A validator to validate whether the given value is an even number or not.
        """
        def __call__(self, value: int):
            if value % 2 != 0:
                raise ValidationError(f"Value '{value}' is not an even number")

    # or use function instead of class
    def validate_even_number(value:int):
        if value % 2 != 0:
            raise ValidationError(f"Value '{value}' is not an even number")
