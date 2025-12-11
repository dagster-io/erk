import asyncio
from collections.abc import Awaitable, Callable, Iterable


async def pmap[A, R](
    func: Callable[[A], Awaitable[R]], iterable: Iterable[A], max_concurrency: int
) -> list[R]:
    """
    Parallel map with limited concurrency.

    Args:
        func: async function to apply
        iterable: items to process
        max_concurrency: maximum number of concurrent tasks

    Returns:
        List of results in the same order as input
    """
    semaphore = asyncio.Semaphore(max_concurrency)

    async def worker(item):
        async with semaphore:
            return await func(item)

    tasks = [asyncio.create_task(worker(item)) for item in iterable]
    return await asyncio.gather(*tasks)
