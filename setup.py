# coding: utf8
import re
import sys

from setuptools import setup

if sys.version_info < (3, 5, 3):
    raise RuntimeError("tortoise requires Python 3.5.3+")


def version():
    verstrline = open('tortoise/__init__.py', "rt").read()
    mob = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", verstrline, re.M)
    if mob:
        return mob.group(1)
    else:
        raise RuntimeError("Unable to find version string")


def requirements():
    return open('requirements.txt', "rt").read().splitlines()


setup(
    # Application name:
    name="tortoise-orm",

    # Version number:
    version=version(),

    # Application author details:
    author="Andrey Bondar",
    author_email="andrey@bondar.ru",

    # License
    license='Apache License Version 2.0',

    # Packages
    packages=["tortoise"],

    # Include additional files into the package
    include_package_data=True,

    # Details
    url="https://github.com/Zeliboba5/tortoise-orm",
    description="Easy async ORM for python, built with relations in mind",
    long_description=open('README.rst', 'r').read(),
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: PL/SQL',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Operating System :: POSIX',
        'Operating System :: MacOS :: MacOS X',
    ],
    keywords=('sql mysql postgres psql '
              'relational database rdbms '
              'orm object mapper'),

    # Dependent packages (distributions)
    install_requires=requirements(),
)
