# Plan: Remove default MCP server configuration

## Context

`.mcp.json` at the project root configures an "erk" MCP server that Claude Code auto-discovers and starts on every session. This causes failures in CI (the erk-mcp package isn't installed via `uv tool install`) and isn't needed by default for local development either.

## Change

Delete `/workspaces/erk/.mcp.json`.

Users who want the MCP server can add it to their user-level Claude Code settings or a local `.mcp.json` (gitignored).

## Verification

- CI `plan-implement` runs no longer show `"mcp_servers":[{"name":"erk","status":"failed"}]`
- Local Claude Code sessions start without attempting to launch the erk MCP server
