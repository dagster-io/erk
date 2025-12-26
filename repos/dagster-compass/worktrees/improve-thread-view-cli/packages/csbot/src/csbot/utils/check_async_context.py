import asyncio


def is_async_context() -> bool:
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


def ensure_not_in_async_context() -> None:
    if is_async_context():
        raise Exception("Cannot run in async context")
