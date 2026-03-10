---
title: "Adding Machine JSON Commands"
read_when:
  - "adding a new machine-readable JSON command"
  - "exposing a command via MCP"
  - "creating result dataclasses for JSON output"
  - "stacking @mcp_exposed and @machine_command decorators"
  - "adding a new CLI command with both human and machine output"
  - "creating a new command subpackage"
tripwires:
  - action: "placing @mcp_exposed below @machine_command in decorator stack"
    warning: "@mcp_exposed must be ABOVE @machine_command. Correct order: @mcp_exposed > @machine_command > @click.command."
  - action: "creating a result dataclass without to_json_dict() method"
    warning: "Result dataclasses should implement to_json_dict() for custom serialization. Without it, the serializer falls back to dataclasses.asdict() which may not handle complex types correctly."
  - action: "adding --json flag to a human command"
    warning: "Machine JSON output belongs in the `erk json` command tree. Create a machine adapter as json_cli.py in the command's subpackage instead."
  - action: "duplicating fetch/query logic in cli.py instead of calling run_*() from operation.py"
    warning: "cli.py MUST delegate to the operation. The operation is the single source of truth for business logic. cli.py only marshals Click flags into the Request and renders the Result. Never re-fetch, re-query, or re-compute what the operation already returns."
  - action: "eagerly serializing rich objects in the Result dataclass"
    warning: "Result dataclasses should carry rich domain objects (not pre-serialized dicts). Serialization belongs in to_json_dict() only. The human CLI needs rich objects for display; the machine adapter needs to_json_dict() for JSON."
---

# Adding Machine JSON Commands

Step-by-step guide to adding structured JSON output for a CLI command using the `erk json` command tree.

## Architecture

Machine commands live in a separate `erk json` tree, not as flags on human commands:

- **Human command**: `src/erk/cli/commands/foo/cli.py` — Click options, rich terminal output
- **Operation**: `src/erk/cli/commands/foo/operation.py` — Shared business logic
- **Machine adapter**: `src/erk/cli/commands/foo/json_cli.py` — JSON stdin/stdout

## The Operation is the Single Source of Truth

**Both `cli.py` and `json_cli.py` MUST call the operation's `run_*()` function.** The operation owns all business logic: fetching, filtering, sorting, enrichment. The transports only handle marshaling and rendering.

```
cli.py          json_cli.py
  │                 │
  │  Click flags    │  JSON stdin
  │  → Request      │  → Request
  │                 │
  └────┬────────────┘
       │
       ▼
  operation.py
  run_foo(ctx, request) → Result | MachineCommandError
       │
  ┌────┴────────────┐
  │                 │
  ▼                 ▼
cli.py          json_cli.py
Result →        Result →
Rich output     to_json_dict()
```

**Anti-pattern: cli.py re-fetching or re-computing.** If `cli.py` calls `run_foo()` and then makes additional API calls to get data the operation already returned, the operation's Result type is incomplete. Fix the Result, not the CLI.

**Anti-pattern: eagerly serializing in the Result.** If the Result carries `list[dict[str, Any]]` instead of rich domain objects, the human CLI can't render from it without re-fetching. Keep rich objects in the Result; serialize only in `to_json_dict()`.

## Step 1: Create an Operation File

Extract shared logic into an `operation.py` file:

```python
# src/erk/cli/commands/foo/operation.py
from dataclasses import dataclass
from erk_shared.agentclick.machine_command import MachineCommandError

@dataclass(frozen=True)
class FooRequest:
    name: str
    count: int
    verbose: bool

@dataclass(frozen=True)
class FooResult:
    items: list[Item]  # Rich domain objects, not serialized dicts

    def to_json_dict(self) -> dict[str, Any]:
        return {"items": [i.to_dict() for i in self.items], "count": len(self.items)}

def run_foo(ctx: ErkContext, request: FooRequest) -> FooResult | MachineCommandError:
    if not request.name.strip():
        return MachineCommandError(error_type="invalid_input", message="Name required")
    # ... business logic ...
    return FooResult(items=[item_a, item_b])
```

## Step 2: Create the Machine Adapter

```python
# src/erk/cli/commands/foo/json_cli.py
import click
from erk.cli.commands.foo.operation import FooRequest, FooResult, run_foo
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import MachineCommandError, machine_command
from erk_shared.agentclick.mcp_exposed import mcp_exposed

@mcp_exposed(name="foo", description="Do foo operation")
@machine_command(request_type=FooRequest, output_types=(FooResult,))
@click.command("foo")
@click.pass_obj
def json_foo(ctx: ErkContext, *, request: FooRequest) -> FooResult | MachineCommandError:
    return run_foo(ctx, request)
```

## Step 3: Register the Command

Register in the command's subpackage `__init__.py` or the json group:

```python
from erk.cli.commands.foo.json_cli import json_foo
json_group.add_command(json_foo, name="foo")
```

## Step 4: Update the Human Command

The human command marshals Click flags into the Request and renders the Result:

```python
# src/erk/cli/commands/foo/cli.py
@click.command("foo")
@click.argument("name")
@click.option("--count", type=int)
@click.pass_obj
def foo(ctx, *, name, count):
    request = FooRequest(name=name, count=count)
    result = run_foo(ctx, request)
    if isinstance(result, MachineCommandError):
        user_output(click.style(f"Error: {result.message}", fg="red"))
        raise SystemExit(1)
    # Rich human output using result.items directly
    _display_items(result)
```

**cli.py has exactly two jobs:**

1. Marshal Click flags/arguments into a `FooRequest`
2. Render the `FooResult` as rich terminal output

It does NOT fetch data, apply business logic, or duplicate anything the operation does.

## Decorator Stack Order

```
@mcp_exposed(...)        # MCP exposure (optional, outermost)
@machine_command(...)     # Machine command infrastructure
@click.command(...)       # Click command
@click.pass_obj           # Context passing (innermost)
```

## MCP Exposure

`@mcp_exposed` registers the command for MCP tool discovery. At startup, the MCP server walks the Click tree to find commands with `_machine_command_meta` and registers them as tools.

**Source**: `packages/erk-shared/src/erk_shared/agentclick/mcp_exposed.py`

## Worked Examples

### one-shot (`src/erk/cli/commands/one_shot/json_cli.py`)

See the one-shot machine adapter for the canonical example of `@mcp_exposed` / `@machine_command` / `@click.command` layering with the shared `run_one_shot()` operation.

### pr view (`src/erk/cli/commands/pr/view/`)

`PrViewResult` carries all fields needed for both human and machine display. The human `cli.py` renders directly from `PrViewResult` without re-fetching. `to_json_dict()` handles conditional `body` inclusion and datetime serialization.

### pr list (`src/erk/cli/commands/pr/list/`)

`PrListResult` carries `list[PlanRowData]` (rich domain objects), not pre-serialized dicts. The human `cli.py` uses the rows directly for Rich table rendering. Serialization via `serialize_plan_row()` happens only in `to_json_dict()`.
