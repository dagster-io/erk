---
title: "Adding --json to CLI Commands"
read_when:
  - "adding --json flag to a CLI command"
  - "exposing a command via MCP"
  - "creating result dataclasses for JSON output"
  - "stacking @mcp_exposed and @json_command decorators"
tripwires:
  - action: "placing @mcp_exposed below @json_command in decorator stack"
    warning: "@mcp_exposed must be ABOVE @json_command. Correct order: @mcp_exposed > @json_command > @click.command."
  - action: "creating a result dataclass without to_json_dict() method"
    warning: "Result dataclasses should implement to_json_dict() for custom serialization. Without it, emit_json_result() falls back to dataclasses.asdict() which may not handle complex types correctly."
---

# Adding --json to CLI Commands

Step-by-step guide to adding structured JSON output to existing Click commands.

## Decorator Stacking Order

The decorators must be stacked in this exact order (outermost to innermost):

```python
@mcp_exposed(name="pr_list", description="List plans")  # 1. MCP exposure (optional)
@json_command(exclude_json_input=frozenset({"repo_id"}), output_types=(PrListResult,))  # 2. JSON infrastructure
@click.command("list")  # 3. Click command
@click.option(...)  # 4. Options/arguments
@click.pass_obj  # 5. Context passing (innermost)
```

## Step 1: Create a Result Dataclass

```python
@dataclass(frozen=True)
class PrListResult:
    """JSON result for erk pr list."""
    plans: list[dict[str, Any]]
    count: int

    def to_json_dict(self) -> dict[str, Any]:
        return {"plans": self.plans, "count": self.count}
```

Rules:

- Always frozen dataclass
- Implement `to_json_dict()` for any custom serialization needs
- For simple cases, `dataclasses.asdict()` fallback works without `to_json_dict()`
- Conditionally include fields (e.g., `if self.body is not None`)

## Step 2: Add Decorators

```python
@json_command(
    exclude_json_input=frozenset({"repo_id"}),  # Params not accepted via JSON stdin
    output_types=(PrListResult,),                # Must match return annotation
)
```

## Step 3: Return the Result

```python
def pr_list(ctx, ...) -> PrListResult | None:
    # ... business logic ...
    if ctx.json_mode:
        return PrListResult(plans=plan_dicts, count=len(plan_dicts))
    # ... human-readable output ...
    return None
```

The decorator calls `emit_json_result()` on non-None returns when `--json` is active.

## Step 4: Add MCP Exposure (Optional)

```python
@mcp_exposed(
    name="pr_list",
    description="List plans filtered by state and labels"
)
```

- `@mcp_exposed` registers the command in `_MCP_REGISTRY` for MCP tool discovery
- Uses `McpMeta` dataclass to store name and description
- `discover_mcp_commands()` walks the CLI tree to find all registered commands
- Does not modify command behavior — purely metadata annotation

**Source**: `packages/erk-shared/src/erk_shared/agentclick/mcp_exposed.py`

## exclude_json_input

Use for parameters that should not be accepted from JSON stdin:

```python
exclude_json_input=frozenset({"repo_id"})
```

Common exclusions:

- `repo_id` — resolved from git context, not user input
- Context-derived parameters that make no sense in JSON input

## Worked Examples

### pr list (`src/erk/cli/commands/pr/list_cmd.py`)

```python
@mcp_exposed(name="pr_list", description="...")
@json_command(exclude_json_input=frozenset({"repo_id"}), output_types=(PrListResult,))
@click.command("list")
@pr_filter_options
@resolved_repo_option
@click.pass_obj
def pr_list(ctx, ...) -> PrListResult | None:
```

### pr view (`src/erk/cli/commands/pr/view_cmd.py`)

```python
@mcp_exposed(name="pr_view", description="...")
@json_command(exclude_json_input=frozenset({"repo_id"}), output_types=(PrViewResult,))
@click.command("view")
@click.argument("identifier", ...)
@resolved_repo_option
@click.pass_obj
def pr_view(ctx, ...) -> PrViewResult | None:
```

`PrViewResult` demonstrates complex serialization — it uses `_serialize_header_fields()` to handle nested datetime objects and conditionally includes the `body` field.
