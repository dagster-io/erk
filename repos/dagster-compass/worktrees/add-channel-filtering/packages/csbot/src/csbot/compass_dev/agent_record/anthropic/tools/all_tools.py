"""All available tools for recording scenarios."""

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from .calculator_tool import CALCULATOR_TOOLS
from .search_tool import SEARCH_TOOLS
from .weather_tool import WEATHER_TOOLS

# Combine all tools for easy access
ALL_TOOLS: dict[str, Callable[..., Awaitable[Any]]] = {
    **WEATHER_TOOLS,
    **CALCULATOR_TOOLS,
    **SEARCH_TOOLS,
}

# Tool collections by category
TOOL_COLLECTIONS: dict[str, dict[str, Callable[..., Awaitable[Any]]]] = {
    "weather": WEATHER_TOOLS,
    "calculator": CALCULATOR_TOOLS,
    "search": SEARCH_TOOLS,
    "all": ALL_TOOLS,
}


def get_tools(category: str = "all") -> Mapping[str, Callable[..., Awaitable[Any]]]:
    """Get tools by category.

    Args:
        category: Tool category (weather, calculator, search, all)

    Returns:
        Dict of callable tools
    """
    return TOOL_COLLECTIONS.get(category, ALL_TOOLS)


def get_tool_by_name(name: str) -> Callable[..., Awaitable[Any]] | None:
    """Get a specific tool by name.

    Args:
        name: Tool name

    Returns:
        Callable tool or None if not found
    """
    return ALL_TOOLS.get(name)


def list_tool_names():
    """Get list of all available tool names."""
    return list(ALL_TOOLS.keys())
