"""Data models for nomcp MCP wrapper."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True)
class MCPToolInfo:
    """Tool information returned by the MCP client.

    This is a simplified representation of tool metadata.
    """

    name: str
    description: str | None
    inputSchema: dict[str, object] | None


class MCPClientABC(ABC):
    """Abstract base class for MCP clients.

    This defines the interface that MCPWrapper expects from an MCP client.
    Both the real fastmcp.Client and test fakes should implement this interface.
    """

    @abstractmethod
    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        ...

    @abstractmethod
    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Exit async context manager."""
        ...

    @abstractmethod
    async def list_tools(self) -> list[MCPToolInfo]:
        """List available tools from the server."""
        ...

    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: dict[str, object]) -> object:
        """Call a tool on the server."""
        ...


@dataclass(frozen=True)
class MCPToolParameter:
    """Parameter definition for an MCP tool."""

    name: str
    description: str
    type: str
    required: bool


@dataclass(frozen=True)
class MCPTool:
    """Tool definition from an MCP server."""

    name: str
    description: str
    parameters: list[MCPToolParameter]


@dataclass(frozen=True)
class MCPToolResult:
    """Result from calling an MCP tool."""

    data: object
    is_error: bool = False
    error_message: str | None = None
