### 0.6.0

Added `Prefetch` object


### 0.5.0

Added `contains` and other filter modifiers.

Field kwarg `default` not accepts functions.


### 0.4.0

Immutable QuerySet. `unique` flag for fields


### 0.3.0

Added schema generation and more options for fields

```
from tortoise import Tortoise
from tortoise.backends.sqlite.client import SqliteClient
from tortoise.utils import generate_schema

client = SqliteClient(db_name)
await client.create_connection()
Tortoise.init(client)
await generate_schema(client)
```


### 0.2.0

Added filtering and ordering by related models fields

```
await Tournament.filter(
    events__name__in=['1', '3']
).order_by('-events__participants__name').distinct()
```