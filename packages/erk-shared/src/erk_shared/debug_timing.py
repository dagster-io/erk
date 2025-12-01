"""Debug timing utilities for subprocess and API operations."""

import logging
import time
from collections.abc import Generator
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def timed_operation(operation: str) -> Generator[None]:
    """Context manager that logs operation timing on completion.

    Args:
        operation: Human-readable description of the operation
    """
    start_time = time.perf_counter()
    logger.debug("Starting: %s", operation)
    try:
        yield
    finally:
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.debug("Completed in %dms: %s", elapsed_ms, operation)
