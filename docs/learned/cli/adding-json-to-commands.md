---
title: "Adding Machine Commands"
read_when:
  - "adding a machine-readable CLI surface"
  - "exposing a command via MCP"
  - "splitting human and machine CLI commands"
  - "creating request/result dataclasses for CLI operations"
tripwires:
  - action: "adding a --json flag to a human command for new machine behavior"
    warning: "Do not mix human and machine transport. Keep the human command under `erk ...` and add a separate machine command under `erk json ...`."
  - action: "placing @mcp_exposed below @machine_command in decorator stack"
    warning: "@mcp_exposed must be above @machine_command. Correct order: @mcp_exposed > @machine_command > @click.command."
  - action: "implementing machine-only logic directly in the human command"
    warning: "Extract a shared operation first. Human and machine commands should both call the same request/result operation layer."
---

# Adding Machine Commands

Erk no longer adds machine behavior to human commands with `--json`. The pattern is now:

- human command: `erk ...`
- machine command: `erk json ...`
- shared business logic: request/result operation function

## Step 1: Extract a Shared Operation

Create a frozen request dataclass, a result dataclass, and a shared operation function.

```python
@dataclass(frozen=True)
class PrViewRequest:
    identifier: str | None = None
    repo: str | None = None
    full: bool = False


@dataclass(frozen=True)
class PrViewResult:
    number: int
    title: str


def run_pr_view(
    request: PrViewRequest,
    *,
    ctx: ErkContext,
) -> PrViewResult | MachineCommandError:
    ...
```

That operation becomes the single source of truth for validation, repo resolution, gateway calls, and returned data.

## Step 2: Keep the Human Command Human

The human command stays on the normal CLI path and renders styled output.

Pattern:

1. parse Click args/options
2. build the request dataclass
3. call the shared operation
4. convert `MachineCommandError` to `UserFacingCliError`
5. render human output

Do not add `--json`, `--stdin-json`, or transport flags here.

## Step 3: Add the Machine Command Under `erk json`

Create a sibling command in `src/erk/cli/commands/json/`.

```python
@mcp_exposed(name="pr_view", description="View a plan")
@machine_command(
    request_type=PrViewRequest,
    output_types=(PrViewResult,),
)
@click.command("view")
@click.pass_obj
def json_pr_view(
    ctx: ErkContext,
    *,
    request: PrViewRequest,
) -> PrViewResult | MachineCommandError:
    return run_pr_view(request, ctx=ctx)
```

Machine commands should not define separate human options. Their input comes from stdin JSON.

## Step 4: Wire the Command Tree

Add the new command to the `json` group:

- `src/erk/cli/commands/json/group.py`
- nested group modules like `json/pr_group.py` as needed
- `src/erk/cli/cli.py`
- `src/erk/cli/help_formatter.py` if the new top-level group needs help categorization

## Step 5: Expose Through MCP

Only decorate the machine command with `@mcp_exposed`.

The MCP server discovers those commands automatically and invokes `erk json ...`, not the human CLI path. If MCP needs the feature, the command must exist in the machine tree.

## Step 6: Rewrite Tests

Cover all three layers:

- operation tests for the shared request/result logic
- human command tests for UX and error presentation
- machine command tests for stdin parsing, schema, and MCP parity

Useful assertions:

- `erk json ...` returns structured success/error envelopes
- `erk ... --json` is rejected for migrated commands
- MCP-discovered command paths begin with `("json", ...)`

## Canonical Example

The one-shot / `pr list` / `pr view` migration is the reference shape:

- shared operations in `src/erk/cli/commands/*_operation.py`
- human commands in `src/erk/cli/commands/...`
- machine commands in `src/erk/cli/commands/json/...`
