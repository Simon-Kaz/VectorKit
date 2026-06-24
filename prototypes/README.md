# prototypes

One directory per experiment. Each is self-contained: its own `README.md`, an
entry point (usually `main.py`), and any prototype-specific requirements.

Shared connection/config logic belongs in `libs/vectorkit`, not duplicated
here. Import it:

```python
from vectorkit import robot_session
```

When a prototype proves out and becomes something you run regularly, promote
its reusable parts into `libs/` and keep the prototype as a thin example.

## Current

- `hello-vector` - connect, read battery, speak. Pipeline smoke test.
