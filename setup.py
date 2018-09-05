# coding: utf8
import re
import sys

from setuptools import find_packages, setup

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
    packages=find_packages(
        include=['tortoise*'],
        exclude=['tortoise.tests']
    ),

    # Include additional files into the package
    include_package_data=True,

    # Details
    url="https://github.com/tortoise/tortoise-orm",
    description="Easy async ORM for python, built with relations in mind",
    long_description=open('README.rst', 'r').read(),
    project_urls={
        'Documentation': 'https://tortoise-orm.readthedocs.io/',
    },    
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: PL/SQL',
        'Framework :: AsyncIO',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Database',
        'Operating System :: POSIX',
        'Operating System :: MacOS :: MacOS X',
    ],
    keywords=('sql mysql postgres psql '
              'sqlite aiosqlite asyncpg '
              'relational database rdbms '
              'orm object mapper '
              'async asyncio aio'),

    # Dependent packages (distributions)
    install_requires=requirements(),
)
