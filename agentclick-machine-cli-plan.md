# Replace `@json_command` With Separate Human and Machine CLI Adapters

## Summary

This plan converts `agentclick` from the current mixed transport model into a three-layer architecture:

1. Core operations that accept structured request objects and return structured result objects
2. Human-facing Click commands under the existing `erk ...` tree
3. Machine-facing commands under a new `erk json ...` tree

This is a flag-day migration. Convert all current `@json_command` consumers at once:

- `erk one-shot`
- `erk pr list`
- `erk pr view`

Do not preserve the current `--json`, `--stdin-json`, or mixed-input behavior.

## Locked Decisions

These decisions are already made. Do not reopen them during implementation.

- No mixed-source input. A command invocation is either human mode or machine mode, never both.
- Human commands remain under the existing `erk ...` tree and stay optimized for humans.
- Machine commands live under a top-level `erk json ...` tree.
- The true canonical layer is the in-process operation contract: request dataclass -> result dataclass.
- `erk json ...` is a machine transport adapter over that core contract, not the core itself.
- MCP maps to machine commands, not human commands.
- This is an all-at-once migration for the current `@json_command` users. Do not carry a transitional dual model.
- No backwards-compatibility shims for the old mixed transport design.

## Why This Change Exists

The current `@json_command` model mixes three concerns in one decorator:

- human Click parsing
- machine JSON transport
- MCP discovery/schema generation

That creates bad layering:

- JSON input is merged into Click kwargs after parsing
- JSON values can override CLI values implicitly
- JSON validation is derived from Click params, but transport semantics are separate
- MCP claims Click is the source of truth while shelling JSON into the CLI through a different path

The target architecture makes the layers explicit instead:

- core operation semantics live in request/result types and pure operation functions
- human CLI maps ergonomic flags/args into request objects
- machine CLI maps stdin JSON into the same request objects
- MCP rides on the machine CLI surface

## Goals

- Eliminate mixed input behavior entirely
- Eliminate `json_stdout` threading through command implementations
- Eliminate `required_json_input` and `exclude_json_input`
- Make machine command schemas describe the real machine contract, not a filtered projection of human Click params
- Keep human ergonomics flexible without polluting the machine contract
- Keep MCP as a thin subprocess wrapper, but point it at `erk json ...`

## Non-Goals

- Migrating every command in the repo to the machine tree in this PR
- Refactoring unrelated command logic
- Rewriting MCP to call Python functions in-process
- Designing a generic framework for every future command beyond what is needed for the initial `agentclick` replacement

## Target Architecture

### Core layer

Each migrated command gets a request dataclass, a result dataclass, and an operation function:

```python
@dataclass(frozen=True)
class OneShotRequest:
    prompt: str
    model: str | None
    dry_run: bool
    plan_only: bool
    slug: str | None
    dispatch_ref: str | None
    ref_current: bool
    target_repo: str | None


def run_one_shot(request: OneShotRequest, *, ctx: ErkContext) -> OneShotDispatchResult | OneShotDryRunResult:
    ...
```

Rules:

- Request and result types are the canonical contract
- Request/result types are frozen dataclasses
- Core functions must not import `click`
- Core functions must not read stdin, print output, or know whether they were called by human CLI, machine CLI, or MCP

### Human adapter layer

Existing human commands stay where they are:

- `erk one-shot`
- `erk pr list`
- `erk pr view`

Rules:

- Human commands remain ergonomic
- Human-only conveniences stay here, not in the machine contract
- Human adapters may support positional arguments, `--file`, short flags, local inference, richer display output, and human help text
- Human adapters build request dataclasses, call the core function, and render the result
- Human adapters should return `None`, not `Result | None`

### Machine adapter layer

New machine commands live under:

- `erk json one-shot`
- `erk json pr list`
- `erk json pr view`

Rules:

- Input comes from stdin JSON object only
- Output is structured JSON only
- No positional ergonomics
- No mixed input mode
- `--schema` is allowed on machine commands only
- Machine adapters parse stdin JSON, construct request dataclasses, call the core function, serialize results, and emit structured errors

### MCP layer

MCP remains a subprocess wrapper:

- discover machine commands only
- derive tool schemas from machine command metadata
- invoke `erk json ...`
- pass request JSON on stdin
- consume structured JSON stdout

Do not optimize MCP to call core Python functions directly in this refactor.

## Contract Design Rules

These rules are important because they are the reason for the refactor.

### Request contract

- Machine request schemas must describe the machine contract directly
- Do not expose internal helper-only parameters like `repo_id`, `json_stdout`, `stdin_json`, `schema_mode`, or `file_path`
- If a human command needs an ergonomic helper flag, resolve it before constructing the request object

Examples:

- `one-shot` human CLI may keep `--file`, but machine `OneShotRequest` should contain resolved `prompt`, not `file_path`
- `pr list` and `pr view` should accept a human-meaningful optional repo selector in the machine contract, not a `GitHubRepoId` internal object

### Validation contract

- LBYL validation belongs in request construction and core operations, not in transport merging
- Human and machine adapters may have adapter-specific validation only when it is truly transport-specific
- Business-rule validation must live in the core layer so all callers share it

### Output contract

Preserve the existing structured envelope shape unless there is a strong reason not to:

- success: `{"success": true, ...result fields...}`
- error: `{"success": false, "error_type": "...", "message": "..."}`

This minimizes MCP churn while still replacing the old transport model.

## Current Files To Touch

### Core agentclick / MCP infrastructure

- `packages/erk-shared/src/erk_shared/agentclick/json_command.py`
- `packages/erk-shared/src/erk_shared/agentclick/json_schema.py`
- `packages/erk-shared/src/erk_shared/agentclick/mcp_exposed.py`
- `packages/erk-mcp/src/erk_mcp/server.py`

### Root CLI wiring

- `src/erk/cli/cli.py`

### Commands being migrated

- `src/erk/cli/commands/one_shot.py`
- `src/erk/cli/commands/pr/list_cmd.py`
- `src/erk/cli/commands/pr/view_cmd.py`

### Existing logic to reuse carefully

- `src/erk/cli/commands/one_shot_remote_dispatch.py`
- `_pr_list_impl()` in `src/erk/cli/commands/pr/list_cmd.py`

### Tests that will need replacement or major edits

- `packages/erk-shared/tests/unit/agentclick/test_json_command.py`
- `packages/erk-shared/tests/unit/agentclick/test_json_schema.py`
- `packages/erk-mcp/tests/test_server.py`
- `tests/unit/cli/test_json_command.py`
- `tests/unit/cli/test_mcp_cli_sync.py`
- `tests/commands/one_shot/test_one_shot_json.py`

### Docs that will need updates in the same change

- `docs/learned/cli/json-command-decorator.md`
- `docs/learned/cli/adding-json-to-commands.md`
- `docs/learned/integrations/mcp-integration.md`
- `docs/learned/cli/agent-friendly-cli.md`

## Recommended File Layout

It is acceptable to keep the existing `agentclick` package name, but the semantics must change.

Suggested structure:

- `packages/erk-shared/src/erk_shared/agentclick/`
  - machine command wrapper module
  - machine schema module
  - MCP metadata/discovery module
  - shared JSON stdin/stdout helpers
- `src/erk/cli/commands/json/`
  - top-level `json` group
  - `one_shot` machine command
  - `pr` subgroup with `list` and `view`

For core operations, prefer co-located non-Click modules near the existing commands instead of moving command semantics into `erk_shared` unless they are genuinely cross-package.

Examples:

- `src/erk/cli/commands/one_shot_operation.py`
- `src/erk/cli/commands/pr/list_operation.py`
- `src/erk/cli/commands/pr/view_operation.py`

Exact filenames may vary, but keep the boundary clear:

- operation modules: no Click
- human command modules: Click + human rendering
- machine command modules: Click + machine transport

## Implementation Steps

### 1. Replace the `agentclick` abstraction

Create a new machine-command abstraction to replace `@json_command`.

Requirements:

- no merging of JSON and Click kwargs
- no `json_stdout` threading into callbacks
- no input schema generation from human Click params
- machine command metadata must be attached to machine commands directly
- machine commands must support:
  - parse stdin JSON object
  - `--schema`
  - structured success output
  - structured error output

Implementation notes:

- It is fine to rename `json_command.py` and `json_schema.py` if that reduces conceptual confusion
- It is also fine to keep the files and replace their semantics if that minimizes churn
- Do not preserve `exclude_json_input` or `required_json_input`

Deliverables:

- machine command metadata type
- machine command decorator or helper
- schema builder for request/result contracts
- JSON stdin parser and result/error emitter helpers

### 2. Add the `erk json` command tree

Create a new top-level `json` group and register it in `src/erk/cli/cli.py`.

Initial machine command tree:

- `erk json one-shot`
- `erk json pr list`
- `erk json pr view`

Rules:

- machine tree is explicit and regular
- do not mirror every human ergonomic alias
- do not add human-only flags just because the human command has them

Decide whether machine command paths should exactly mirror the human command names. The expected answer here is yes.

### 3. Extract `one-shot` core operation

Split current `src/erk/cli/commands/one_shot.py` into:

- human adapter
- machine adapter
- core operation

Request design:

- include only machine-meaningful fields
- resolved prompt text belongs in the request
- `file_path` does not belong in the machine request contract

Human adapter responsibilities:

- handle prompt positional argument
- handle `--file`
- normalize model aliases
- resolve human ergonomics around local repo and `--repo`
- construct `OneShotRequest`
- call core operation
- render human output

Machine adapter responsibilities:

- parse stdin JSON to `OneShotRequest`
- expose `OneShotRequest` schema
- return structured JSON output only

Core operation responsibilities:

- validate prompt semantics
- resolve target repo semantics
- resolve dispatch ref semantics
- call `dispatch_one_shot_remote()`

Note:

- Reuse `OneShotDispatchResult` and `OneShotDryRunResult` if they already match the core contract
- Do not keep `json_stdout` in the operation signature

### 4. Extract `pr list` core operation

Current `pr list` already has `_pr_list_impl()`. Use that as the starting point, but remove transport branching from it.

Target shape:

- `PrListRequest`
- `PrListResult`
- `run_pr_list(request, *, ctx)`
- human `erk pr list`
- machine `erk json pr list`

Key changes:

- remove `json_stdout` from `_pr_list_impl()` or replace it entirely
- make the core operation always return `PrListResult`
- move table rendering into the human adapter only
- move repo-resolution ergonomics into the human/machine adapters

Important contract choice:

- do not expose `repo_id: GitHubRepoId` as the machine request input
- machine contract should use a user-facing repo selector if remote mode is supported

### 5. Extract `pr view` core operation

`pr view` currently has most of its logic inline. Extract it into a request/result/core shape.

Target shape:

- `PrViewRequest`
- `PrViewResult`
- `run_pr_view(request, *, ctx)`
- human `erk pr view`
- machine `erk json pr view`

Human adapter responsibilities:

- preserve optional `identifier`
- preserve local branch inference when identifier is omitted
- preserve human display output

Machine adapter responsibilities:

- accept structured request JSON only
- expose schema
- return structured result JSON only

Core operation responsibilities:

- resolve identifier semantics
- fetch the plan
- enrich header metadata
- construct `PrViewResult`

### 6. Move MCP to machine commands

Change MCP discovery and execution so that MCP targets the new machine CLI surface.

Required changes:

- `mcp_exposed` metadata should attach to machine commands, not human commands
- discovery should return machine command paths rooted under `erk json`
- subprocess execution should run `["erk", "json", ...]`
- stdin should contain the machine request JSON
- schemas should come from machine command metadata, not human Click introspection

Keep the current subprocess architecture unless forced otherwise.

### 7. Delete the old mixed model

After all three commands are migrated:

- remove `@json_command` from the command tree
- remove `--json`, `--stdin-json`, and `--schema` from human commands
- remove `json_stdout` arguments from command implementations
- remove `exclude_json_input` and `required_json_input`
- remove Click-param-derived JSON input logic

Do not leave dormant infrastructure around "just in case."

### 8. Rewrite tests around the new boundaries

Replace transport-mixing tests with layered tests.

### Core operation tests

Add focused tests for:

- request validation
- semantic invariants
- result construction

These should not use Click unless the function under test is an adapter.

### Human CLI tests

Add tests for:

- flag/argument mapping into request objects
- ergonomic behavior like `--file`
- human output rendering
- absence of legacy machine flags on human commands

### Machine CLI tests

Add tests for:

- stdin JSON parsing
- unknown/missing field handling
- structured success/error envelopes
- `--schema`
- zero tolerance for mixed input behavior

### MCP tests

Update tests so they assert:

- discovery finds machine commands
- subprocess calls go through `erk json ...`
- tool schemas match machine command schemas

### Command-specific regression tests

Retain coverage for the important command behaviors already tested today, but rewrite them against the new adapter/core boundaries.

### 9. Update documentation in the same PR

The current learned docs describe the old architecture and will become actively misleading after the code changes.

Update or replace:

- `docs/learned/cli/json-command-decorator.md`
- `docs/learned/cli/adding-json-to-commands.md`
- `docs/learned/integrations/mcp-integration.md`
- `docs/learned/cli/agent-friendly-cli.md`

Required documentation changes:

- human CLI vs machine CLI vs core operation distinction
- `erk json ...` as the machine command tree
- no mixed input model
- MCP targeting machine commands
- request/result contracts as the source of truth

## Validation Checklist

The implementation is done only when all of the following are true:

- `erk one-shot` works without any machine flags
- `erk pr list` works without any machine flags
- `erk pr view` works without any machine flags
- `erk json one-shot` accepts stdin JSON and emits structured JSON
- `erk json pr list` accepts stdin JSON and emits structured JSON
- `erk json pr view` accepts stdin JSON and emits structured JSON
- `erk json ... --schema` works for each migrated machine command
- MCP discovers the machine commands and executes them through `erk json ...`
- no migrated human command advertises or accepts `--json` or `--stdin-json`
- no migrated core operation accepts `json_stdout`
- old `@json_command` tests are removed or replaced
- docs no longer claim Click params are the JSON source of truth

Use repo-standard validation tooling. Do not run raw pytest/ruff/ty directly if the repo expects those through the devrun flow.

## Risks and Gotchas

- The biggest risk is accidentally preserving old concepts under new names. If a new machine decorator still derives its contract from human Click params, the refactor has failed.
- Do not expose human helper parameters in the machine schema just because they were previously Click params.
- `one-shot` currently weakens Click requiredness to support JSON input. Undo that coupling rather than carrying it into the new design.
- `pr list` already has partial extraction; use it, but remove the `json_stdout` branch instead of wrapping it with more adapter code.
- `pr view` currently mixes inference, fetch, enrichment, and display. Split those responsibilities cleanly.
- MCP tests currently encode the old command path. Update them in the same change.
- Learned docs currently state that Click is the source of truth for MCP/JSON. That statement must change.

## Acceptance Criteria For Review

A reviewer should be able to inspect the final diff and see:

- a clear core request/result operation for each migrated command
- human adapters that are thinner than today
- machine adapters under `erk json ...`
- MCP pointed at the machine adapters
- no mixed transport semantics left in `agentclick`
- docs and tests aligned with the new model

If any migrated command still takes both human flags and machine JSON in the same code path, the migration is incomplete.
