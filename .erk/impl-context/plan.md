# Plan: Create Agent-Friendly CLI Principles Document

## Context

Capture research from this session (article analysis, gws CLI analysis, erk state audit) as a learned doc so Objective #9009 implementers have full context.

## Steps

1. Write the document below verbatim to `docs/learned/cli/agent-friendly-cli.md`
2. Run `erk docs sync`
3. Commit new doc + regenerated index/tripwire files

## Complete Document

Write this file to `docs/learned/cli/agent-friendly-cli.md`:

````
---
title: "Agent-Friendly CLI Design Principles"
read_when:
  - "adding --json flag to a CLI command"
  - "creating or modifying MCP tools"
  - "implementing structured JSON output for CLI commands"
  - "working on agent-friendly CLI patterns"
  - "implementing erk schema command"
tripwires:
  - action: "adding --json flag to a command without using @json_output decorator"
    warning: "Use the shared @json_output decorator from src/erk/cli/json_output.py. Do not manually implement JSON serialization in individual commands."
  - action: "returning non-zero exit code when --json flag is active"
    warning: "JSON mode must always exit 0. Errors are communicated via {success: false, error_type, message} in stdout JSON, not via exit codes."
  - action: "naming a JSON output flag --json-output instead of --json"
    warning: "Standardized flag name is --json (not --json-output). See agent-friendly-cli.md for the naming decision."
  - action: "emitting human-readable text to stdout when --json is active"
    warning: "When --json is active, stdout must contain only the JSON result object. Human output goes to stderr via user_output()."
  - action: "creating an MCP tool that parses human-readable CLI output"
    warning: "MCP tools must call CLI commands with --json flag and parse structured JSON. Never parse human-readable text output."
---

# Agent-Friendly CLI Design Principles

Principles and patterns for making erk's CLI agent-friendly — enabling MCP tools, Claude Code skills, and other AI agents to invoke erk commands and parse structured responses.

Derived from analysis of:

- [Justin Poehnelt's "Rewrite Your CLI for AI Agents"](https://justin.poehnelt.com/posts/rewrite-your-cli-for-ai-agents/)
- The [Google Workspace CLI (gws)](https://github.com/googleworkspace/cli) reference implementation
- Erk's existing CLI patterns and MCP server

Tracked by Objective #9009.

## Core Principle: Dual Surface, Single Binary

Every erk command serves two audiences through a single implementation:

- **Human users** (default): Styled, colored output via `user_output()` to stderr
- **Agent consumers** (`--json` flag): Structured JSON via `machine_output()` to stdout

The `--json` flag is the toggle. When active:

- Success → `{"success": true, ...command-specific fields...}` on stdout, exit 0
- Error → `{"success": false, "error_type": "machine_readable", "message": "Human-readable"}` on stdout, exit 0
- Human output still goes to stderr (agents ignore it, humans see progress)

This mirrors the existing exec script pattern in `src/erk/cli/script_output.py`, extended to top-level commands.

## Patterns Adopted

### 1. `--json` Output Flag (Per-Command)

Each command opts in via a shared `@json_output` Click decorator (to be built in `src/erk/cli/json_output.py`). The decorator:

- Adds `--json` as a Click option
- When active: catches the command's return value, serializes to JSON, emits to stdout
- When active + error: catches `UserFacingCliError`, emits structured JSON error, exits 0
- When inactive: command runs normally with human output

**Flag name**: Standardized as `--json` (not `--json-output`). Existing `--json-output` flags on `objective view` and `objective check` get renamed.

**Per-command, not global**: Each command explicitly opts in. Commands where JSON doesn't make sense (like `init`, `completion`) don't get the flag. This matches the existing pattern (`wt create --json`, `pr log --json`).

### 2. Structured JSON Errors

All JSON-mode errors follow the exec script contract:

```json
{
  "success": false,
  "error_type": "auth_required",
  "message": "GitHub authentication required.\nRun 'gh auth login' to authenticate."
}
```

Key rules:

- `error_type` is machine-readable, snake_case (e.g., `auth_required`, `invalid_argument`, `not_found`)
- `message` is human-readable, may contain newlines and formatting guidance
- Always exit 0 — agents parse JSON, not exit codes
- `UserFacingCliError` gains an `error_type` field (default `None` for backwards compat)

### 3. `--dry-run` as JSON

Mutating commands with `--dry-run` emit a JSON preview when combined with `--json`:

```json
{
  "success": true,
  "dry_run": true,
  "prompt": "fix the bug",
  "branch": "oneshot-fix-bug-03-08-1234",
  "pr_title": "One-shot: fix the bug",
  "target": "owner/repo"
}
```

This enables agents to validate what would happen before executing. The `one-shot` command already has `--dry-run` with human output — it just needs the JSON path.

### 4. Schema Introspection

`erk schema <command-path>` dumps JSON Schema for any command's inputs and outputs:

```json
{
  "command": "one-shot",
  "input": {
    "type": "object",
    "properties": {
      "prompt": { "type": "string", "description": "Task description" },
      "model": {
        "type": "string",
        "description": "Model to use (haiku/h, sonnet/s, opus/o)"
      },
      "dry_run": {
        "type": "boolean",
        "description": "Show what would happen without executing"
      },
      "plan_only": {
        "type": "boolean",
        "description": "Create a plan remotely without implementing it"
      }
    },
    "required": ["prompt"]
  },
  "output": {
    "type": "object",
    "properties": {
      "success": { "type": "boolean" },
      "pr_number": { "type": "integer" },
      "pr_url": { "type": "string" },
      "run_id": { "type": "string" },
      "branch_name": { "type": "string" }
    }
  }
}
```

Implementation approach:

- Walk Click's command tree programmatically (`cli.commands`, `params`)
- Map Click types to JSON Schema types: `str` → `string`, `int` → `integer`, `bool`/is_flag → `boolean`, `click.Path` → `string`
- Output schemas registered on the `@json_output` decorator via result type (frozen dataclass → schema via `dataclasses.fields()`)
- Support dotted paths: `erk schema pr.list`, `erk schema objective.view`

### 5. MCP Follows CLI

The MCP server (`packages/erk-mcp/src/erk_mcp/server.py`) delegates to CLI subprocess calls. As commands gain `--json`, MCP tools upgrade to use it:

**Before** (current state — fragile):

```python
def one_shot(prompt: str) -> str:
    result = _run_erk(["one-shot", prompt])
    return result.stdout  # Raw human-readable text
```

**After** (target — structured):

```python
def one_shot(prompt: str, model: str | None = None, dry_run: bool = False) -> str:
    args = ["one-shot", "--json", prompt]
    if model is not None:
        args.extend(["--model", model])
    if dry_run:
        args.append("--dry-run")
    result = _run_erk(args)
    return result.stdout  # Structured JSON
```

MCP tools expand organically — each phase of the objective adds MCP tools for the commands it JSON-ifies.

## Patterns Skipped (and Why)

These patterns from the gws CLI / article were evaluated and deliberately skipped for erk:

| Pattern                                  | Why Skipped                                                                                                                                           |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Raw JSON input** (`--json` body flag)  | Erk uses well-defined Click options, not REST API payloads. Click options are already typed and validated.                                             |
| **NDJSON pagination**                    | Erk datasets are small (tens of plans, not millions of Drive files). Single JSON response is fine.                                                     |
| **Field masks** (`--fields`)             | Erk responses are already compact. No need to filter fields.                                                                                          |
| **`--format json\|table\|yaml\|csv`**   | Erk only needs two modes: human (default) and JSON (`--json`). Adding table/yaml/csv is unnecessary complexity.                                       |
| **Discovery-driven MCP generation**      | Gws auto-generates MCP tools from Google's Discovery Document. Erk's MCP server is thin enough that manual tool registration works fine.              |
| **Model Armor / response sanitization**  | Erk doesn't fetch untrusted external content that could contain prompt injection.                                                                     |
| **Input validation hardening**           | Good idea but deferred. Not part of the initial steel thread. Can be added later as agents become primary consumers.                                  |

## JSON Output Contract

Every `--json` response follows this contract:

### Success Response

```json
{
  "success": true
  // ...command-specific fields
}
```

### Error Response

```json
{
  "success": false,
  "error_type": "snake_case_category",
  "message": "Human-readable error description"
}
```

### Dry-Run Response

```json
{
  "success": true,
  "dry_run": true
  // ...preview of what would happen
}
```

### Rules

1. `success` field is always present and always first
2. JSON-mode commands always exit 0
3. Errors are communicated in the JSON body, not via exit codes
4. `error_type` is machine-readable, suitable for switch/match statements
5. `message` is human-readable, may contain newlines
6. No ANSI color codes or Click styling in JSON-mode output
7. Output goes to stdout via `machine_output()` (not `click.echo()`)

## Existing Foundation (What Erk Already Has)

Erk has strong building blocks that the agent-friendly work extends:

### Output Routing (Already Correct)

`packages/erk-shared/src/erk_shared/output/output.py`:

- `user_output()` → stderr (human-readable, styled)
- `machine_output()` → stdout (structured, machine-parseable)

This separation is exactly what agent-friendly CLI needs. The gap is that top-level commands only use `user_output()` and return `None`.

### Exec Script JSON Pattern (Already Working)

`src/erk/cli/script_output.py`:

```python
def exit_with_error(error_type: str, message: str) -> NoReturn:
    error_json = json.dumps(
        {"success": False, "error_type": error_type, "message": message},
        indent=2,
    )
    click.echo(error_json)
    raise SystemExit(0)
```

This is the exact error contract we're extending to top-level commands.

### Existing --json Flags (Ad-Hoc)

| Command          | Flag              | Notes                          |
| ---------------- | ----------------- | ------------------------------ |
| `wt create`      | `--json`          | Manually implements JSON output |
| `pr log`         | `--json`          | Manually implements JSON output |
| `objective view`  | `--json-output`   | Inconsistent flag name          |
| `objective check` | `--json-output`   | Inconsistent flag name          |

These prove the pattern works. The infrastructure work extracts the shared decorator.

### OneShotDispatchResult (Already Exists)

`src/erk/cli/commands/one_shot_remote_dispatch.py`:

```python
@dataclass(frozen=True)
class OneShotDispatchResult:
    pr_number: int
    run_id: str
    branch_name: str
```

The structured data is already computed and returned — it's just not serialized to JSON. The `dispatch_one_shot_remote()` function returns this but `one_shot` Click command ignores the return value.

### MCP Server (Thin Wrapper)

`packages/erk-mcp/src/erk_mcp/server.py`:

- 3 tools: `plan_list`, `plan_view`, `one_shot`
- All call `_run_erk(args)` subprocess
- `plan_list` and `plan_view` already get JSON (from exec scripts)
- `one_shot` gets human text (the gap we're fixing)

## Key Files Reference

| File                                                         | Role                                                        |
| ------------------------------------------------------------ | ----------------------------------------------------------- |
| `src/erk/cli/json_output.py`                                 | **New**: Shared `@json_output` decorator + result protocol  |
| `src/erk/cli/ensure.py`                                      | **Modify**: Add `error_type` to `UserFacingCliError`        |
| `src/erk/cli/commands/one_shot.py`                           | Steel thread: add `--json` flag                             |
| `src/erk/cli/commands/one_shot_remote_dispatch.py`           | Already has `OneShotDispatchResult` dataclass                |
| `packages/erk-mcp/src/erk_mcp/server.py`                    | MCP server: upgrade to use `--json`                         |
| `src/erk/cli/script_output.py`                               | Existing JSON error pattern to align with                   |
| `packages/erk-shared/src/erk_shared/output/output.py`       | `user_output()` / `machine_output()` definitions            |
| `src/erk/cli/commands/schema_cmd.py`                         | **New**: `erk schema` command                               |

## Reference: Google Workspace CLI (gws)

The gws CLI at `/Users/schrockn/code/githubs/googleworkspace/cli` served as the reference implementation. Key architectural insights:

- **Rust + clap** framework, **Discovery Document-driven**: Single binary works for all Google APIs by reading API schemas at runtime
- **`--format json|table|yaml|csv`** global flag with JSON as default
- **`gws schema <method>`** dumps full method signatures from Discovery docs
- **Structured JSON errors** with `error_type`, `message`, `reason` fields, plus actionable hints (e.g., "enable API at this URL")
- **`--dry-run`** returns JSON preview: `{"dry_run": true, "url": "...", "method": "POST", "body": {...}}`
- **MCP server** (`gws mcp -s drive,gmail`) auto-generates tool definitions from Discovery docs
- **Helper commands** with `+` prefix (e.g., `gws drive +upload`) add convenience operations alongside API methods
- **NDJSON pagination** with `--page-all` for streaming large result sets
- **Input validation**: Path traversal rejection, control character filtering, resource ID validation
- **100+ SKILL.md files** with YAML frontmatter for agent-specific invariants per command

Key source files in gws:

- `src/executor.rs` - HTTP execution, response handling, pagination
- `src/formatter.rs` - Multi-format output (JSON, table, YAML, CSV)
- `src/schema.rs` - Schema introspection from Discovery docs
- `src/error.rs` - Structured JSON error handling
- `src/mcp_server.rs` - MCP server exposing API methods as tools
- `src/validate.rs` - Input validation (path traversal, control chars)
- `src/helpers/` - Service-specific helper commands (drive +upload, sheets +append)

## Reference: Article Key Recommendations

From "Rewrite Your CLI for AI Agents" by Justin Poehnelt:

1. **Raw JSON payloads over custom flags** — Accept full API payloads as structured input
2. **Runtime schema introspection** — Make the CLI itself the canonical documentation source
3. **Context window discipline** — Field masks, NDJSON pagination to limit response size
4. **Input hardening against hallucinations** — Path traversal rejection, control character filtering, resource ID validation
5. **Agent skills** — Ship SKILL.md / CONTEXT.md files with agent-specific invariants
6. **Multi-surface exposure** — Same CLI exposed via MCP, Gemini, env vars for headless auth
7. **Safety rails** — Dry-run validation, response sanitization
8. **Incremental path** — `--output json` → validate inputs → schema → field masks → dry-run → skills → MCP
````
