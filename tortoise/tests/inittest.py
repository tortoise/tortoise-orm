"""
Only for coverage of initialiser/finaliser portions of our tests
"""
from tortoise.contrib.test import finalizer, initializer

initializer()
finalizer()
