---
title: "Adding Machine-Readable Commands"
read_when:
  - "adding a machine-readable command to erk"
  - "exposing a command via MCP"
  - "creating result dataclasses for JSON output"
  - "extracting core operations from CLI commands"
tripwires:
  - action: "creating a result dataclass without to_json_dict() method"
    warning: "Result dataclasses should implement to_json_dict() for custom serialization. Without it, the fallback uses dataclasses.asdict() which may not handle complex types correctly."
  - action: "adding Click options to a machine command"
    warning: "Machine commands derive input from request dataclasses, not Click options. Only @click.pass_obj is allowed alongside @machine_command."
---

# Adding Machine-Readable Commands

Step-by-step guide to adding a new machine-readable command under `erk json ...`.

## Architecture

Each command has three layers:

1. **Core operation** (`*_operation.py`) — request/result dataclasses + pure business logic
2. **Human adapter** (existing Click command) — Click options, human-readable output
3. **Machine adapter** (`erk json ...`) — `@machine_command`, JSON-in/JSON-out

## Step 1: Create Request/Result Dataclasses

Create a `*_operation.py` file with frozen dataclasses using simple types only:

```python
@dataclass(frozen=True)
class MyRequest:
    prompt: str                    # Required field
    model: str | None = None       # Optional field
    dry_run: bool = False          # Optional with default

@dataclass(frozen=True)
class MyResult:
    value: str
    count: int

    def to_json_dict(self) -> dict[str, Any]:
        return {"value": self.value, "count": self.count}
```

Add a `run_my_operation()` function that takes the request and returns the result.

## Step 2: Create Machine Command

Add a file under `src/erk/cli/commands/json/`:

```python
@machine_command(
    request_type=MyRequest,
    result_types=(MyResult,),
    name="my_tool",
    description="Does something useful",
)
@click.command("my-tool")
@click.pass_obj
def json_my_tool(ctx: ErkContext, *, request: MyRequest) -> MyResult:
    return run_my_operation(request, ctx=ctx)
```

Register in the appropriate `json` group's `__init__.py`.

## Step 3: Refactor Human Command

Update the existing human command to use the same core operation:

```python
@click.command("my-tool")
@click.option("--prompt", required=True)
@click.pass_obj
def my_tool(ctx: ErkContext, *, prompt: str) -> None:
    request = MyRequest(prompt=prompt)
    result = run_my_operation(request, ctx=ctx)
    # Render result for humans
    click.echo(f"Value: {result.value}")
```

## Step 4: MCP Discovery

Machine commands are automatically discovered as MCP tools. The `@machine_command` decorator stores `MachineCommandMeta` on the command, and the MCP server walks the Click tree to find all such commands.

No additional decorator needed — just `@machine_command` is sufficient.

## Command Group Structure

Machine commands live under `src/erk/cli/commands/json/`. Run `erk json --help` to see the current list of available machine commands.

## Worked Examples

- **one-shot**: `src/erk/cli/commands/json/one_shot.py` + `src/erk/cli/commands/one_shot_operation.py`
- **pr list**: `src/erk/cli/commands/json/pr/list_cmd.py` + `src/erk/cli/commands/pr/list_operation.py`
- **pr view**: `src/erk/cli/commands/json/pr/view_cmd.py` + `src/erk/cli/commands/pr/view_operation.py`
