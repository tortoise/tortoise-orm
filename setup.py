# coding: utf8

import ast

import sys
from setuptools import setup


if sys.version_info < (3, 5, 3):
    raise RuntimeError("tortoise requires Python 3.5.3+")


def readme():
    with open('README.rst', 'rb') as f:
        return f.read().decode('UTF-8')


def version():
    path = 'tortoise/__init__.py'
    with open(path, 'rU') as file:
        t = compile(file.read(), path, 'exec', ast.PyCF_ONLY_AST)
        for node in (n for n in t.body if isinstance(n, ast.Assign)):
            if len(node.targets) == 1:
                name = node.targets[0]
                if isinstance(name, ast.Name) and \
                        name.id in ('__version__', '__version_info__', 'VERSION'):
                    v = node.value
                    if isinstance(v, ast.Str):
                        return v.s

                    if isinstance(v, ast.Tuple):
                        r = []
                        for e in v.elts:
                            if isinstance(e, ast.Str):
                                r.append(e.s)
                            elif isinstance(e, ast.Num):
                                r.append(str(e.n))
                        return '.'.join(r)


with open('requirements.txt') as f:
    required = f.read().splitlines()


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
    long_description=readme(),

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
    install_requires=required,
)
