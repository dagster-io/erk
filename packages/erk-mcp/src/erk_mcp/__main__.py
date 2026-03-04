import argparse
import os

from erk_mcp.server import create_mcp


def _parse_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Erk MCP server.")
    parser.add_argument("--host", default=os.getenv("ERK_MCP_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=_parse_int_env("ERK_MCP_PORT", 9000))
    parser.add_argument(
        "--transport",
        choices=["streamable-http", "stdio"],
        default="streamable-http",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = _parse_args()
    mcp = create_mcp()
    if args.transport == "stdio":
        mcp.run()
    else:
        print(f"Starting erk MCP server on http://{args.host}:{args.port}/mcp")
        mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
