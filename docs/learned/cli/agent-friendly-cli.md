---
title: "Agent-Friendly CLI Design Principles"
read_when:
  - "adding a machine-readable CLI surface"
  - "creating or modifying MCP tools"
  - "designing human and machine CLI separation"
  - "working on agent-friendly CLI patterns"
tripwires:
  - action: "adding a --json flag to a human command for a new agent-facing API"
    warning: "Do not extend human commands with machine transport. Add a separate machine command under `erk json ...`."
  - action: "creating an MCP tool that parses human-readable CLI output"
    warning: "MCP must target explicit machine commands and consume structured stdin/stdout JSON only."
  - action: "combining Click options and stdin JSON in one command surface"
    warning: "Keep the transport model single-purpose. Human commands use Click options; machine commands use stdin JSON."
  - action: "returning non-zero exit codes for machine-command validation errors"
    warning: "Machine commands communicate expected failures via `{success: false, error_type, message}` envelopes."
---

# Agent-Friendly CLI Design Principles

The current Erk pattern is not "one command with a `--json` mode." It is two command surfaces sharing one operation layer.

## Core Principle

Use three layers:

1. shared operation function with frozen request/result dataclasses
2. human command under `erk ...`
3. machine command under `erk json ...`

This avoids a mixed transport model where one command tries to be both interactive CLI and machine API.

## Human Surface

Human commands:

- use Click arguments and options
- render styled or formatted output
- raise `UserFacingCliError` for expected user failures

They should not gain new `--json`, `--stdin-json`, or similar transport flags for agent use.

## Machine Surface

Machine commands:

- live under `erk json ...`
- read a JSON object from stdin
- return structured JSON on stdout
- use `@machine_command(..., output_types=...)`
- expose schema with `--schema`

Their output contract is:

```json
{ "success": true, "...": "result fields" }
```

or

```json
{ "success": false, "error_type": "snake_case", "message": "..." }
```

## Shared Operation Layer

The operation layer owns:

- validation
- repo and remote resolution
- gateway calls
- canonical request/result types

Human and machine commands should be thin adapters over that layer. If the business logic only exists in the Click callback, the command is not agent-friendly enough.

## MCP Follows the Machine Tree

MCP is a thin wrapper over machine commands, not over human output.

Rules:

- decorate only `erk json ...` commands with `@mcp_exposed`
- let MCP discovery walk the Click tree and find those commands
- have the server invoke `erk json ...` and pipe params as stdin JSON

If there is no machine command, there is no MCP tool.

## Why This Split Works Better

Compared to `--json` on human commands, the explicit machine tree:

- removes ambiguous input rules
- keeps human help text and UX clean
- makes schemas derive from stable request/result contracts
- gives MCP one canonical transport path
- makes migrations flag-day instead of carrying long-term compatibility shims

## Migration Checklist

When converting an agent-facing command:

1. extract request/result dataclasses and a shared operation
2. keep the human command focused on human UX
3. add `erk json ...` sibling command with `@machine_command`
4. move `@mcp_exposed` to the machine command
5. remove old mixed-mode flags and tests
6. update learned docs and MCP parity tests

## Scope Note

This guidance is for agent-facing top-level commands like `one-shot`, `pr list`, and `pr view`.

Some exec scripts and older commands still expose JSON flags for script use. Do not copy that pattern into new top-level agent surfaces.
