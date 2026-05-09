# logging-mixin

**Class-bound structured logging with auto-injected correlation IDs for Python services.**

Replaces module-level loggers in business logic with per-class loggers that automatically inject correlation IDs and class context into every log record. Enables clean distributed tracing without boilerplate.

## Why?

Production services need correlation IDs for tracing requests through distributed systems. Traditional approaches require passing context through every function or managing global state:

```python
# Traditional approach: manual context passing (boilerplate)
logger = logging.getLogger(__name__)

def create_user(name: str, correlation_id: str):
    logger.info("Creating user", extra={"correlation_id": correlation_id, "name": name})
    # Must thread correlation_id through every call
    save_user(name, correlation_id)

def save_user(name: str, correlation_id: str):
    logger.info("Saving user", extra={"correlation_id": correlation_id, "name": name})
```

`logging-mixin` solves this with automatic injection:

```python
from logging_mixin import LoggingMixin

class UserService(LoggingMixin):
    def create_user(self, name: str):
        self.log_info("Creating user", name=name)
        # correlation_id automatically injected by LoggingMixin
        self.save_user(name)

    def save_user(self, name: str):
        self.log_info("Saving user", name=name)
        # correlation_id still available, no parameter needed
```

## Installation

```bash
pip install logging-mixin
```

Requires Python 3.10+.

### Optional framework extras

```bash
# Django support
pip install logging-mixin[django]

# FastAPI support
pip install logging-mixin[fastapi]

# AWS Lambda support
pip install logging-mixin[aws-lambda]

# All together
pip install logging-mixin[django,fastapi,aws-lambda]

# Development (includes all extras + testing tools)
pip install logging-mixin[dev]
```

## Quick Start

### 1. Create a service using LoggingMixin

```python
from logging_mixin import LoggingMixin

class OrderService(LoggingMixin):
    def create_order(self, user_id: int, items: list[str]):
        self.log_info("order.create", user_id=user_id, item_count=len(items))
        # Logs with:
        #   logger name: "myapp.services.OrderService"
        #   extra: {"correlation_id": "abc123", "user_id": 123, "item_count": 3}
        ...
```

### 2. Set correlation ID in your framework

#### Django

Add the middleware to `settings.py`:

```python
MIDDLEWARE = [
    "logging_mixin.adapters.django.CorrelationIdMiddleware",
    # ... other middleware
]
```

#### FastAPI

Add middleware:

```python
from fastapi import FastAPI
from logging_mixin.adapters.fastapi import correlation_id_middleware

app = FastAPI()
app.add_middleware(correlation_id_middleware)
```

#### AWS Lambda

Call in handler:

```python
from logging_mixin.adapters.aws_lambda import setup_correlation_id

def lambda_handler(event, context):
    setup_correlation_id(event, context)
    # Now LoggingMixin can access correlation_id
    ...
```

### 3. Use in background tasks

Correlation IDs automatically propagate to Celery tasks, background jobs, and async functions via Python's `contextvars`:

```python
from celery import shared_task
from logging_mixin import LoggingMixin

@shared_task
def process_order(order_id: int):
    service = OrderService()
    service.log_info("order.processing", order_id=order_id)
    # Inherits correlation_id from the original request context
```

## Design

### Instance-only (no @classmethod/@staticmethod)

LoggingMixin's `log_*` methods are instance methods. They cannot be called from `@classmethod` or `@staticmethod` because they read `self._logger`:

```python
class MyService(LoggingMixin):
    def instance_method(self):
        self.log_info("works")  # ✓ OK

    @classmethod
    def class_method(cls):
        self.log_info("FAILS")  # ✗ TypeError: missing 1 required positional argument 'self'

    @staticmethod
    def static_method():
        self.log_info("FAILS")  # ✗ TypeError
```

**Workaround:** Use module-level logger for class methods and manually inject correlation ID:

```python
import logging
from logging_mixin import get_correlation_id

logger = logging.getLogger(__name__)

class MyService(LoggingMixin):
    def instance_method(self):
        self.log_info("instance.event")  # ✓ Automatic injection

    @classmethod
    def class_method(cls):
        cid = get_correlation_id()
        logger.info("class.event", extra={"correlation_id": cid or "-"})  # ✓ Manual injection
```

### Correlation ID lifecycle

Correlation IDs are stored in a `contextvars.ContextVar`, which means they:
- Survive async/await boundaries (async-safe)
- Cross thread boundaries when using thread pool executors
- Are automatically reset at the start of each HTTP request (Django/FastAPI middleware)
- Propagate to background tasks (Celery, threading, async)

### Composition with masking

LoggingMixin automatically composes with masking libraries. If your instance has a `mask_for_logging()` method (e.g., from a masking mixin), its output is added to the log record:

```python
from logging_mixin import LoggingMixin
from some_library import MaskingMixin

class Response(LoggingMixin, MaskingMixin):
    def trace(self):
        self.log_debug("response")
        # Logs with extra: {"correlation_id": "...", "instance": <masked dict>}
```

## API Reference

### LoggingMixin

Class-bound logger providing five methods:

```python
class Service(LoggingMixin):
    def do_thing(self):
        self.log_debug("event", detail="verbose")      # DEBUG level
        self.log_info("event", status="ok")             # INFO level
        self.log_warning("event", issue="slow")         # WARNING level
        self.log_error("event", error="failure")        # ERROR level
        self.log_exception("event")                     # ERROR level + traceback
```

Each method:
- Takes an event name (string) and optional keyword arguments
- Automatically injects correlation_id into the log record's `extra` dict
- Reads from the per-class logger (`module.ClassName`)
- Composes with `mask_for_logging()` if available

### Context functions

```python
from logging_mixin import get_correlation_id, set_correlation_id, clear_correlation_id

# Get the current correlation ID (returns None if not set)
cid = get_correlation_id()

# Manually set (for background tasks, tests, non-request contexts)
set_correlation_id("abc123def456")

# Clear (useful for test isolation)
clear_correlation_id()
```

### Framework adapters

#### Django middleware

Automatically sets correlation ID from `X-Correlation-ID` header or generates UUID.

```python
from logging_mixin.adapters.django import CorrelationIdMiddleware

MIDDLEWARE = ["logging_mixin.adapters.django.CorrelationIdMiddleware", ...]
```

#### FastAPI dependency

Two approaches:

```python
# Middleware (auto for all routes):
from logging_mixin.adapters.fastapi import correlation_id_middleware
app.add_middleware(correlation_id_middleware)

# Or dependency (per-route opt-in):
from fastapi import Depends
from logging_mixin.adapters.fastapi import correlation_id_dependency

@app.get("/items/")
def get_items(cid: str = Depends(correlation_id_dependency)):
    ...
```

#### AWS Lambda

```python
from logging_mixin.adapters.aws_lambda import setup_correlation_id

def lambda_handler(event, context):
    setup_correlation_id(event, context)
    # Now LoggingMixin can access correlation_id via get_correlation_id()
    ...
```

## Testing

LoggingMixin is test-friendly:

```python
import logging
from logging_mixin import LoggingMixin, set_correlation_id

class TestMyService:
    def test_logs_with_correlation_id(self, caplog):
        set_correlation_id("test-123")

        service = MyService()
        with caplog.at_level(logging.INFO):
            service.do_something()

        assert caplog.records[0].correlation_id == "test-123"
```

## Design Principles

- **Class-bound:** Each class gets its own logger (`module.ClassName`) for clean grouping
- **Instance-only:** Methods read `self._logger` (cannot be used from @classmethod/@staticmethod)
- **Async-safe:** Uses `contextvars.ContextVar` (survives async/await, thread pools)
- **Framework-agnostic:** Core mixin has zero framework dependencies
- **Composable:** Works naturally with masking mixins and other mixins
- **Zero boilerplate:** No function signature changes needed

## Trade-offs

- **Cannot use in @classmethod/@staticmethod:** Use module-level logger + manual correlation ID injection instead
- **Requires ContextVar setup:** Framework adapters or manual `set_correlation_id()` call needed
- **Implicit behavior:** Correlation ID is silently injected (can be surprising if not expected)

## License

Apache 2.0 — see LICENSE file.

## See Also

- [contextvars](https://docs.python.org/3/library/contextvars.html) — Python standard library
- [logging](https://docs.python.org/3/library/logging.html) — Python standard library
- [Django middleware](https://docs.djangoproject.com/en/stable/topics/http/middleware/) — Django framework
- [FastAPI middleware](https://fastapi.tiangolo.com/tutorial/middleware/) — FastAPI framework
