.. _contrib_dameng:

=====================
Dameng-specific Features
=====================

This module contains Dameng-specific features for Tortoise ORM.

Connection String
=================

Dameng database connection strings should use the ``dm://`` URL scheme:

.. code-block:: python3

    # Basic connection
    'dm://username:password@host:port/database'
    
    # With charset
    'dm://username:password@host:port/database?charset=utf8'
    
    # Default port is 5236
    'dm://username:password@host/database'

Fields
======

Dameng-specific field types provide native support for Dameng database features.

XMLField
--------

.. autoclass:: tortoise.contrib.dameng.fields.XMLField
    :members:

Store and retrieve XML data:

.. code-block:: python3

    from tortoise.models import Model
    from tortoise.contrib.dameng.fields import XMLField
    
    class Document(Model):
        id = fields.IntField(primary_key=True)
        content = XMLField()
    
    # Usage
    doc = await Document.create(
        content='<root><item>value</item></root>'
    )

IntervalField
-------------

.. autoclass:: tortoise.contrib.dameng.fields.IntervalField
    :members:

Store time intervals:

.. code-block:: python3

    from tortoise.models import Model
    from tortoise.contrib.dameng.fields import IntervalField
    
    class Task(Model):
        id = fields.IntField(primary_key=True)
        duration = IntervalField()
    
    # Usage
    task = await Task.create(
        duration=timedelta(hours=2, minutes=30)
    )

RowIDField
----------

.. autoclass:: tortoise.contrib.dameng.fields.RowIDField
    :members:

Access Dameng's internal ROWID:

.. code-block:: python3

    from tortoise.models import Model
    from tortoise.contrib.dameng.fields import RowIDField
    
    class Record(Model):
        id = fields.IntField(primary_key=True)
        row_id = RowIDField()

Functions
=========

Dameng-specific SQL functions for use in queries.

Date/Time Functions
-------------------

.. autoclass:: tortoise.contrib.dameng.functions.ToChar
    :members:

Convert date/time to string:

.. code-block:: python3

    from tortoise.contrib.dameng.functions import ToChar
    
    # Get formatted date
    await Model.annotate(
        date_str=ToChar('created_at', 'YYYY-MM-DD')
    ).values('date_str')

.. autoclass:: tortoise.contrib.dameng.functions.ToDate
    :members:

Convert string to date:

.. code-block:: python3

    from tortoise.contrib.dameng.functions import ToDate
    
    # Parse date string
    await Model.filter(
        created_at__gte=ToDate('2024-01-01', 'YYYY-MM-DD')
    )

.. autoclass:: tortoise.contrib.dameng.functions.SysDate
    :members:

Get current system date:

.. code-block:: python3

    from tortoise.contrib.dameng.functions import SysDate
    
    # Filter by current date
    await Model.filter(
        created_at__lte=SysDate()
    )

String Functions
----------------

.. autoclass:: tortoise.contrib.dameng.functions.InitCap
    :members:

Capitalize first letter of each word:

.. code-block:: python3

    from tortoise.contrib.dameng.functions import InitCap
    
    await Model.annotate(
        title_case=InitCap('name')
    ).values('title_case')

.. autoclass:: tortoise.contrib.dameng.functions.Instr
    :members:

Find substring position:

.. code-block:: python3

    from tortoise.contrib.dameng.functions import Instr
    
    # Find position of '@' in email
    await Model.annotate(
        at_pos=Instr('email', '@')
    ).values('at_pos')

.. autoclass:: tortoise.contrib.dameng.functions.LPad
    :members:

Left-pad string:

.. code-block:: python3

    from tortoise.contrib.dameng.functions import LPad
    
    # Pad ID with zeros
    await Model.annotate(
        padded_id=LPad('id', 5, '0')
    ).values('padded_id')

.. autoclass:: tortoise.contrib.dameng.functions.RPad
    :members:

Right-pad string:

.. code-block:: python3

    from tortoise.contrib.dameng.functions import RPad
    
    # Pad name with spaces
    await Model.annotate(
        padded_name=RPad('name', 20, ' ')
    ).values('padded_name')

Utility Functions
-----------------

.. autoclass:: tortoise.contrib.dameng.functions.NVL
    :members:

Replace NULL values:

.. code-block:: python3

    from tortoise.contrib.dameng.functions import NVL
    
    # Replace NULL with default
    await Model.annotate(
        status=NVL('status', 'active')
    ).values('status')

.. autoclass:: tortoise.contrib.dameng.functions.Decode
    :members:

SQL CASE expression:

.. code-block:: python3

    from tortoise.contrib.dameng.functions import Decode
    
    # Map values
    await Model.annotate(
        category=Decode(
            'type',
            1, 'Basic',
            2, 'Premium',
            3, 'Enterprise',
            'Unknown'
        )
    ).values('category')

.. autoclass:: tortoise.contrib.dameng.functions.RowNum
    :members:

Get row number:

.. code-block:: python3

    from tortoise.contrib.dameng.functions import RowNum
    
    # Get first 10 rows
    await Model.filter(
        RowNum() <= 10
    ).values()

Aggregate Functions
-------------------

.. autoclass:: tortoise.contrib.dameng.functions.ListAgg
    :members:

Aggregate values into string:

.. code-block:: python3

    from tortoise.contrib.dameng.functions import ListAgg
    
    # Concatenate names
    await Model.annotate(
        all_names=ListAgg('name', ',')
    ).group_by('department')

Performance Considerations
==========================

Connection Pooling
------------------

The Dameng backend includes an enterprise-grade connection pool with:

- Automatic connection health checks
- Connection reuse and recycling
- Configurable pool size (min/max connections)
- Idle timeout management
- Automatic reconnection on failure

Configure connection pooling:

.. code-block:: python3

    await Tortoise.init(
        db_url='dm://user:pass@host:5236/db',
        modules={'models': ['app.models']},
        # Connection pool settings
        minsize=1,
        maxsize=5,
        connection_timeout=10,
        pool_recycle=3600,  # Recycle connections after 1 hour
    )

Parameter Binding
-----------------

The Dameng backend automatically converts Tortoise's parameter placeholders
(`:1`, `:2`, etc.) to Dameng's native format (`?`). This ensures compatibility
while maintaining security through proper parameter binding.

Thread Safety
-------------

Since dmPython driver operations are synchronous, the Dameng backend uses
ThreadPoolExecutor to run database operations without blocking the async event
loop. This ensures thread safety while maintaining async compatibility.

Limitations
===========

- Dameng does not support certain PostgreSQL-specific features like ARRAY fields
- Some advanced JSON operations may have limited support
- Full-text search capabilities differ from PostgreSQL's implementation
- Spatial/GIS features require Dameng's spatial extension

Migration Notes
===============

When migrating from other databases to Dameng:

1. **Data Types**: Review field mappings as some types may differ
2. **SQL Syntax**: Some queries may need adjustment for Dameng-specific syntax
3. **Functions**: Use Dameng-specific functions from this contrib module
4. **Indexes**: Review index strategies as Dameng may have different optimization patterns

Example Migration
-----------------

.. code-block:: python3

    # PostgreSQL model
    class OldModel(Model):
        data = fields.JSONField()
        tags = ArrayField()  # Not supported in Dameng
    
    # Dameng model
    class NewModel(Model):
        data = fields.JSONField()
        tags = fields.TextField()  # Store as JSON string instead