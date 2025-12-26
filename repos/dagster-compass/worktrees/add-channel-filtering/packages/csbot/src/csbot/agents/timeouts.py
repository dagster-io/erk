import asyncio
from collections.abc import AsyncIterator


async def iterator_with_timeout[T](
    async_iter: AsyncIterator[T], timeout: float
) -> AsyncIterator[T]:
    """Async iterator wrapper that adds timeout behavior to each iteration.
    Args:
        async_iter: The async iterator to wrap
        timeout: Timeout in seconds for each iteration
    Yields:
        Events from the wrapped iterator
    Raises:
        TimeoutError: If any single iteration exceeds the timeout
    """
    iterator = async_iter.__aiter__()

    while True:
        try:
            event = await asyncio.wait_for(iterator.__anext__(), timeout=timeout)
            yield event
        except StopAsyncIteration:
            break
