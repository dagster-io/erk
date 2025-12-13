import asyncio
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any


def sync_to_async[**P, T](func: Callable[P, T]) -> Callable[P, Coroutine[Any, Any, T]]:
    """
    Decorator that converts a sync function to an async function by wrapping it in
    asyncio.to_thread.

    Uses generic types to preserve type information for both parameters and return values.

    Args:
        func: The sync function to convert

    Returns:
        An async coroutine function that wraps the original sync function
    """

    @wraps(func)
    async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return await asyncio.to_thread(func, *args, **kwargs)

    return async_wrapper
