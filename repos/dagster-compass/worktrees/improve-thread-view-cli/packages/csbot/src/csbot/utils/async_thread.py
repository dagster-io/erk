"""Utilities for converting sync code to async using thread execution.

This module provides the `async_thread` decorator and establishes patterns for cleanly
separating sync and async implementations to avoid the "async/sync duality annoyance".

## Overview

The async/sync duality problem occurs when you have business logic that needs to be
available in both synchronous and asynchronous contexts. Traditional approaches either:
1. Duplicate the implementation (bad)
2. Make everything async and use asyncio.to_thread everywhere (scattered, boilerplate)
3. Write sync code and wrap entire methods (manual, repetitive)

This module provides a pattern that solves this cleanly using:
- **Protocols**: Define the sync interface
- **Sync implementation**: Contains all business logic
- **Async wrapper**: Uses @async_thread decorator for automatic conversion
- **Type checking**: Ensures async wrapper implements the protocol correctly

## Usage Pattern

### Step 1: Define a Protocol

Create a runtime-checkable protocol that defines your sync interface:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class MyServiceProtocol(Protocol):
    def get_data(self, key: str) -> dict[str, Any]:
        ...

    def process_item(self, item: Item, options: ProcessOptions | None) -> Result:
        ...
```

### Step 2: Implement the Sync Version

Create a concrete sync implementation with all your business logic:

```python
class SyncMyService:
    def __init__(self, backend: Backend) -> None:
        self.backend = backend

    def get_data(self, key: str) -> dict[str, Any]:
        # All your business logic goes here
        result = self.backend.fetch(key)
        processed = self._validate_and_transform(result)
        return processed

    def process_item(self, item: Item, options: ProcessOptions | None) -> Result:
        # More business logic
        validated_item = self._validate_item(item)
        config = options or self._get_default_options()
        return self._execute_processing(validated_item, config)

    def _validate_and_transform(self, data: Any) -> dict[str, Any]:
        # Private helper methods stay here
        ...
```

### Step 3: Create the Async Wrapper

Create an async wrapper that delegates to the sync implementation:

```python
from csbot.utils.async_thread import async_thread

class MyService:
    def __init__(self, sync_service: MyServiceProtocol) -> None:
        self._sync = sync_service

    @async_thread
    def get_data(self, key: str) -> dict[str, Any]:
        ...

    @async_thread
    def process_item(self, item: Item, options: ProcessOptions | None) -> Result:
        ...
```

### Step 4: Add Type Checking (Optional but Recommended)

Ensure your async wrapper correctly implements the protocol:

```python
if TYPE_CHECKING:
    # This will cause a type error if MyService doesn't match MyServiceProtocol
    _: MyServiceProtocol = MyService(SyncMyService(...))  # type: ignore[abstract]
```

### Step 5: Usage

```python
# Create the sync implementation
backend = Backend(connection_string)
sync_service = SyncMyService(backend)

# Create the async wrapper
async_service = MyService(sync_service)

# Use it asynchronously
data = await async_service.get_data("some_key")
result = await async_service.process_item(item, options)
```

## Key Benefits

1. **Single Source of Truth**: All business logic lives in the sync implementation
2. **No Duplication**: Async wrapper contains no business logic, only threading
3. **Type Safety**: Protocol ensures async wrapper matches sync interface
4. **Easy Testing**: Test sync logic directly without async complexity
5. **Reusable Pattern**: Same approach works for any sync/async separation

## Implementation Notes

- The `@async_thread` decorator expects the async wrapper to have a `_sync` attribute
- Method names must match between sync implementation and async wrapper
- The decorator automatically handles argument forwarding and return value conversion
- All sync methods are executed using `asyncio.to_thread` for proper async behavior

## Real Example

See `csbot.contextengine.cronjob_manager` for a complete implementation:
- `UserCronStorageProtocol`: Protocol definition
- `SyncUserCronStorage`: Sync implementation with business logic
- `UserCronStorage`: Async wrapper using @async_thread decorator

## Common Pitfalls

1. **Forgetting `_sync` attribute**: The decorator expects `self._sync` to exist
2. **Method name mismatches**: Sync and async method names must match exactly
3. **Missing protocol methods**: Async wrapper must implement all protocol methods
4. **Type annotation mismatches**: Return types must match between sync and async versions
"""

from __future__ import annotations

import asyncio
import functools
from typing import (
    TYPE_CHECKING,
    Any,
    ParamSpec,
    TypeVar,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

P = ParamSpec("P")
R = TypeVar("R")


def async_thread[**P, R](f: Callable[P, R]) -> Callable[P, Coroutine[Any, Any, R]]:
    """Decorator to convert sync methods to async by running them in a thread.

    This decorator is designed to work with async wrapper classes that delegate
    to sync implementations. It automatically:

    1. Extracts `self` from the method arguments
    2. Gets the corresponding sync method from `self._sync`
    3. Calls the sync method with remaining arguments using `asyncio.to_thread`
    4. Returns the result as an awaitable

    Requirements:
    - The async wrapper class must have a `_sync` attribute containing the sync implementation
    - The sync implementation must have a method with the same name as the decorated method
    - Method signatures must match between sync and async versions

    Args:
        f: The async method to be converted. The method body is ignored (use `...`)

    Returns:
        An async version of the method that delegates to the sync implementation

    Example:
        ```python
        class AsyncService:
            def __init__(self, sync_service: ServiceProtocol):
                self._sync = sync_service

            @async_thread
            def process_data(self, data: str) -> Result:
                ...  # Implementation is handled by decorator
        ```
    """

    @functools.wraps(f)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # Get self from args - we know it has _sync attribute from context
        self = args[0]  # type: ignore[misc]
        # Get the actual method from the sync object
        sync_method = getattr(self._sync, f.__name__)  # type: ignore[attr-defined]
        # Call it with the remaining args
        return await asyncio.to_thread(sync_method, *args[1:], **kwargs)

    return wrapper
