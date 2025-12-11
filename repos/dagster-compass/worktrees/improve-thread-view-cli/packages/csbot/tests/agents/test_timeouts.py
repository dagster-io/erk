import asyncio

import pytest

from csbot.agents.timeouts import iterator_with_timeout


class TestIteratorWithTimeout:
    """Test cases for iterator_with_timeout function."""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        """Test normal iteration works without timeout."""

        async def simple_async_iter():
            for i in range(3):
                yield i
                await asyncio.sleep(0.01)  # Small delay to simulate async work

        result = []
        async for item in iterator_with_timeout(simple_async_iter(), timeout=1.0):
            result.append(item)

        assert result == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_slow_iter_throws(self):
        """Test that slow iterator raises TimeoutError."""

        async def slow_async_iter():
            for i in range(3):
                yield i
                await asyncio.sleep(0.5)  # Each iteration takes 0.5 seconds

        result = []
        with pytest.raises(asyncio.TimeoutError):
            async for item in iterator_with_timeout(slow_async_iter(), timeout=0.1):
                result.append(item)

        # Should have collected the first item before timing out on the second iteration
        assert len(result) == 1  # First item yielded, then timeout on second iteration

    @pytest.mark.asyncio
    async def test_slow_loop_body_does_not_throw(self):
        """Test that slow loop body processing doesn't cause timeout."""

        async def fast_async_iter():
            for i in range(3):
                yield i
                await asyncio.sleep(0.01)  # Fast iteration

        result = []
        async for item in iterator_with_timeout(fast_async_iter(), timeout=0.1):
            # Simulate slow processing in the loop body
            await asyncio.sleep(0.2)  # This should not cause timeout
            result.append(item)

        assert result == [0, 1, 2]
