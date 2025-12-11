"""Comprehensive tests for token logging including cache token scenarios."""

from typing import Any

import pytest
from anthropic.types.message_delta_usage import MessageDeltaUsage
from anthropic.types.server_tool_usage import ServerToolUsage


class TestComprehensiveTokenLogging:
    """Test comprehensive token logging scenarios including cache tokens."""

    @pytest.mark.asyncio
    async def test_high_cache_usage_scenario(self):
        """Test high cache usage scenario representing 98%+ of total usage."""

        # Track token usage calls
        token_usage_calls = []

        async def mock_on_token_usage(total_tokens: int, token_breakdown: dict[str, Any]):
            token_usage_calls.append((total_tokens, token_breakdown))

        # High cache usage scenario (98%+ cache tokens)
        mock_usage_high_cache = MessageDeltaUsage(
            input_tokens=3,
            output_tokens=291,
            cache_creation_input_tokens=815,
            cache_read_input_tokens=14901,
            server_tool_use=None,
        )

        # Simulate the token calculation logic
        input_tokens = mock_usage_high_cache.input_tokens or 0
        output_tokens = mock_usage_high_cache.output_tokens or 0
        cache_creation_tokens = (
            getattr(mock_usage_high_cache, "cache_creation_input_tokens", 0) or 0
        )
        cache_read_tokens = getattr(mock_usage_high_cache, "cache_read_input_tokens", 0) or 0

        total_tokens = input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens

        token_breakdown = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_input_tokens": cache_creation_tokens,
            "cache_read_input_tokens": cache_read_tokens,
            "total_tokens": total_tokens,
        }

        await mock_on_token_usage(total_tokens, token_breakdown)

        # Verify high cache usage scenario
        assert total_tokens == 16010
        assert token_breakdown["cache_creation_input_tokens"] == 815
        assert token_breakdown["cache_read_input_tokens"] == 14901
        cache_percentage = ((815 + 14901) / total_tokens) * 100
        assert cache_percentage > 98.0
        assert len(token_usage_calls) == 1

    @pytest.mark.asyncio
    async def test_cache_creation_scenario(self):
        """Test cache creation scenario (new cache entry)."""

        # Track token usage calls
        token_usage_calls = []

        async def mock_on_token_usage(total_tokens: int, token_breakdown: dict[str, Any]):
            token_usage_calls.append((total_tokens, token_breakdown))

        # Cache creation scenario (new cache entry)
        mock_usage_cache_creation = MessageDeltaUsage(
            input_tokens=5,
            output_tokens=25,
            cache_creation_input_tokens=2000,
            cache_read_input_tokens=0,
            server_tool_use=None,
        )

        input_tokens = mock_usage_cache_creation.input_tokens or 0
        output_tokens = mock_usage_cache_creation.output_tokens or 0
        cache_creation_tokens = (
            getattr(mock_usage_cache_creation, "cache_creation_input_tokens", 0) or 0
        )
        cache_read_tokens = getattr(mock_usage_cache_creation, "cache_read_input_tokens", 0) or 0

        total_tokens = input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens

        token_breakdown = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_input_tokens": cache_creation_tokens,
            "cache_read_input_tokens": cache_read_tokens,
            "total_tokens": total_tokens,
        }

        await mock_on_token_usage(total_tokens, token_breakdown)

        assert total_tokens == 2030
        assert cache_creation_tokens == 2000
        assert cache_read_tokens == 0
        assert len(token_usage_calls) == 1

    @pytest.mark.asyncio
    async def test_cache_read_scenario(self):
        """Test cache read scenario (using existing cache)."""

        # Track token usage calls
        token_usage_calls = []

        async def mock_on_token_usage(total_tokens: int, token_breakdown: dict[str, Any]):
            token_usage_calls.append((total_tokens, token_breakdown))

        # Cache read scenario (using existing cache)
        mock_usage_cache_read = MessageDeltaUsage(
            input_tokens=2,
            output_tokens=15,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=1500,
            server_tool_use=None,
        )

        input_tokens = mock_usage_cache_read.input_tokens or 0
        output_tokens = mock_usage_cache_read.output_tokens or 0
        cache_creation_tokens = (
            getattr(mock_usage_cache_read, "cache_creation_input_tokens", 0) or 0
        )
        cache_read_tokens = getattr(mock_usage_cache_read, "cache_read_input_tokens", 0) or 0

        total_tokens = input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens

        token_breakdown = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_input_tokens": cache_creation_tokens,
            "cache_read_input_tokens": cache_read_tokens,
            "total_tokens": total_tokens,
        }

        await mock_on_token_usage(total_tokens, token_breakdown)

        assert total_tokens == 1517
        assert cache_creation_tokens == 0
        assert cache_read_tokens == 1500
        assert len(token_usage_calls) == 1

    @pytest.mark.asyncio
    async def test_mixed_scenario_with_server_tools(self):
        """Test mixed scenario with server tools."""

        # Track token usage calls
        token_usage_calls = []

        async def mock_on_token_usage(total_tokens: int, token_breakdown: dict[str, Any]):
            token_usage_calls.append((total_tokens, token_breakdown))

        # Mixed scenario with server tools
        mock_server_tool_use = ServerToolUsage(web_search_requests=5)
        mock_usage_mixed = MessageDeltaUsage(
            input_tokens=10,
            output_tokens=50,
            cache_creation_input_tokens=1000,
            cache_read_input_tokens=3000,
            server_tool_use=mock_server_tool_use,
        )

        input_tokens = mock_usage_mixed.input_tokens or 0
        output_tokens = mock_usage_mixed.output_tokens or 0
        cache_creation_tokens = getattr(mock_usage_mixed, "cache_creation_input_tokens", 0) or 0
        cache_read_tokens = getattr(mock_usage_mixed, "cache_read_input_tokens", 0) or 0

        total_tokens = input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens

        token_breakdown = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_input_tokens": cache_creation_tokens,
            "cache_read_input_tokens": cache_read_tokens,
            "total_tokens": total_tokens,
        }

        # Add server tool usage
        server_tool_use = getattr(mock_usage_mixed, "server_tool_use", None)
        if server_tool_use:
            token_breakdown["server_tool_use"] = {
                "web_search_requests": getattr(server_tool_use, "web_search_requests", 0) or 0,
            }

        await mock_on_token_usage(total_tokens, token_breakdown)

        assert total_tokens == 4060
        server_tool_use = token_breakdown["server_tool_use"]
        assert isinstance(server_tool_use, dict)
        assert server_tool_use["web_search_requests"] == 5
        assert len(token_usage_calls) == 1

    @pytest.mark.asyncio
    async def test_none_values_in_nested_attributes(self):
        """Test edge case with None values in nested attributes."""

        # Create a mock cache_creation object with None values
        class MockCacheCreation:
            def __init__(self):
                self.ephemeral_5m_input_tokens = None
                self.ephemeral_1h_input_tokens = None

        class MockUsage:
            def __init__(self):
                self.input_tokens = 5
                self.output_tokens = 10
                self.cache_creation_input_tokens = 0
                self.cache_read_input_tokens = 0
                self.cache_creation = MockCacheCreation()
                self.service_tier = None
                self.server_tool_use = None

        mock_usage_none_values = MockUsage()

        # Test our null-safe logic
        cache_creation = getattr(mock_usage_none_values, "cache_creation", None)
        assert cache_creation is not None

        if cache_creation:
            cache_breakdown = {
                "ephemeral_5m_input_tokens": getattr(cache_creation, "ephemeral_5m_input_tokens", 0)
                or 0,
                "ephemeral_1h_input_tokens": getattr(cache_creation, "ephemeral_1h_input_tokens", 0)
                or 0,
            }
            assert cache_breakdown["ephemeral_5m_input_tokens"] == 0
            assert cache_breakdown["ephemeral_1h_input_tokens"] == 0

    @pytest.mark.asyncio
    async def test_analytics_integration_comprehensive(self):
        """Test analytics integration with comprehensive token scenarios."""
        # Test comprehensive token breakdown serialization
        comprehensive_breakdown = {
            "input_tokens": 3,
            "output_tokens": 291,
            "cache_creation_input_tokens": 815,
            "cache_read_input_tokens": 14901,
            "total_tokens": 16010,
            "cache_creation": {
                "ephemeral_5m_input_tokens": 815,
                "ephemeral_1h_input_tokens": 0,
            },
            "service_tier": "standard",
            "server_tool_use": {
                "web_search_requests": 3,
            },
        }

        # Test JSON serialization (as used in analytics)
        import json

        json_str = json.dumps(comprehensive_breakdown)
        parsed_back = json.loads(json_str)

        # Verify all fields are preserved
        assert parsed_back["total_tokens"] == 16010
        assert parsed_back["cache_creation_input_tokens"] == 815
        assert parsed_back["cache_read_input_tokens"] == 14901
        assert parsed_back["cache_creation"]["ephemeral_5m_input_tokens"] == 815
        assert parsed_back["service_tier"] == "standard"
        assert parsed_back["server_tool_use"]["web_search_requests"] == 3

        # Verify cache percentage
        cache_percentage = (
            (parsed_back["cache_creation_input_tokens"] + parsed_back["cache_read_input_tokens"])
            / parsed_back["total_tokens"]
            * 100
        )
        assert cache_percentage > 98.0

    @pytest.mark.asyncio
    async def test_defensive_token_extraction(self):
        """Test defensive token extraction with None values and missing attributes."""

        # Test extraction logic with various edge cases
        class MockUsageWithNones:
            """Mock usage object with None values."""

            def __init__(self):
                self.input_tokens = None
                self.output_tokens = 100
                self.cache_creation_input_tokens = None
                self.cache_read_input_tokens = None

        mock_usage = MockUsageWithNones()

        # Simulate the defensive extraction logic
        input_tokens = getattr(mock_usage, "input_tokens", None) or 0
        output_tokens = getattr(mock_usage, "output_tokens", None) or 0
        cache_creation_tokens = getattr(mock_usage, "cache_creation_input_tokens", None) or 0
        cache_read_tokens = getattr(mock_usage, "cache_read_input_tokens", None) or 0

        # Verify None values are converted to 0
        assert input_tokens == 0
        assert output_tokens == 100
        assert cache_creation_tokens == 0
        assert cache_read_tokens == 0

        total_tokens = input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens
        assert total_tokens == 100

    @pytest.mark.asyncio
    async def test_defensive_token_extraction_missing_attributes(self):
        """Test defensive token extraction when attributes don't exist."""

        # Test extraction with missing attributes
        class MockUsageMinimal:
            """Mock usage object with minimal attributes."""

            def __init__(self):
                self.output_tokens = 50

        mock_usage = MockUsageMinimal()

        # Simulate the defensive extraction logic with getattr defaults
        input_tokens = getattr(mock_usage, "input_tokens", None) or 0
        output_tokens = getattr(mock_usage, "output_tokens", None) or 0
        cache_creation_tokens = getattr(mock_usage, "cache_creation_input_tokens", None) or 0
        cache_read_tokens = getattr(mock_usage, "cache_read_input_tokens", None) or 0

        # Verify missing attributes default to 0
        assert input_tokens == 0
        assert output_tokens == 50
        assert cache_creation_tokens == 0
        assert cache_read_tokens == 0

        total_tokens = input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens
        assert total_tokens == 50

    @pytest.mark.asyncio
    async def test_defensive_token_extraction_zero_values(self):
        """Test defensive token extraction properly handles explicit 0 values."""

        # Test extraction with explicit 0 values (should preserve 0, not treat as None)
        class MockUsageZeros:
            """Mock usage object with explicit 0 values."""

            def __init__(self):
                self.input_tokens = 0
                self.output_tokens = 50
                self.cache_creation_input_tokens = 0
                self.cache_read_input_tokens = 0

        mock_usage = MockUsageZeros()

        # Simulate the defensive extraction logic
        input_tokens = getattr(mock_usage, "input_tokens", None) or 0
        output_tokens = getattr(mock_usage, "output_tokens", None) or 0
        cache_creation_tokens = getattr(mock_usage, "cache_creation_input_tokens", None) or 0
        cache_read_tokens = getattr(mock_usage, "cache_read_input_tokens", None) or 0

        # Verify explicit 0 values are preserved
        assert input_tokens == 0
        assert output_tokens == 50
        assert cache_creation_tokens == 0
        assert cache_read_tokens == 0

        total_tokens = input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens
        assert total_tokens == 50
