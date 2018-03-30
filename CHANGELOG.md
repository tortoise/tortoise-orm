### 0.2.0

Added filtering and ordering by related models fields

```
await Tournament.filter(
    events__name__in=['1', '3']
).order_by('-events__participants__name').distinct()
```