"""Request tracking for test assertions."""

from queue import Queue


class ReceivedRequests:
    """Drains the mock server's request queue and provides assertion helpers.

    Call drain() after test actions complete to collect all recorded requests,
    then use get_count() and get_bodies() for assertions.
    """

    def __init__(self, queue: Queue) -> None:  # type: ignore[type-arg]
        self._queue = queue
        self._requests: dict[str, list[dict]] = {}  # type: ignore[type-arg]

    def drain(self) -> None:
        """Drain all pending requests from the queue."""
        while not self._queue.empty():
            path, body = self._queue.get_nowait()
            if path not in self._requests:
                self._requests[path] = []
            self._requests[path].append(body)

    def get_count(self, path: str) -> int:
        """Return the number of requests received for a given endpoint."""
        return len(self._requests.get(path, []))

    def get_bodies(self, path: str) -> list[dict]:  # type: ignore[type-arg]
        """Return all recorded request bodies for a given endpoint."""
        return list(self._requests.get(path, []))

    def get_all_paths(self) -> list[str]:
        """Return all paths that received requests."""
        return list(self._requests.keys())

    def reset(self) -> None:
        """Clear all recorded requests."""
        self._requests.clear()
        # Also drain any remaining items from queue
        while not self._queue.empty():
            self._queue.get_nowait()
