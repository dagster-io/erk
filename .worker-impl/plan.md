# Plan: Standardize Kit JSON Commands with Automatic Context Passing

## Goal

Enhance the `@kit_json_command` decorator to automatically pass Click context to all kit CLI commands, enabling standardization across the codebase.

## Current State

**Two patterns exist:**
1. `@kit_json_command` (1 command) - auto JSON serialization, auto schema docs, no context
2. Manual pattern (8+ commands) - `@click.pass_context` + manual `json.dumps()` + `SchemaCommand`

**Problem:** Commands needing context can't use `@kit_json_command`, leading to inconsistency and boilerplate.

## Commands In Scope

Commands with typed dataclass return types that output JSON:

| Command | File | Needs Context | Current Pattern |
|---------|------|---------------|-----------------|
| parse-issue-reference | erk/ | No | @kit_json_command |
| find-project-dir | erk/ | No | Manual + SchemaCommand |
| mark-impl-started | erk/ | Yes | Manual + @click.pass_context |
| mark-impl-ended | erk/ | Yes | Manual + @click.pass_context |
| post-start-comment | erk/ | Yes | Manual + @click.pass_context |
| post-pr-comment | erk/ | Yes | Manual + @click.pass_context |
| update-dispatch-info | erk/ | Yes | Manual + @click.pass_context |
| get-pr-commit-message | gt/ | No | Manual |

## Design Decision: Exit Code Handling

Some commands (mark-impl-started, mark-impl-ended, post-start-comment, etc.) use "graceful degradation" - they always exit 0 even on error to support `|| true` patterns in slash commands.

**Approach:** Add `exit_on_error` parameter to `@kit_json_command`:
- `exit_on_error=True` (default): Exit 1 on error_type result
- `exit_on_error=False`: Always exit 0 (graceful degradation)

## Implementation Steps

### Step 1: Enhance `@kit_json_command` decorator

File: `packages/dot-agent-kit/src/dot_agent_kit/cli/schema.py`

Update the decorator to:
1. Automatically apply `@click.pass_context`
2. Inject `ctx` as first positional argument to wrapped function
3. Add `exit_on_error: bool = True` parameter

```python
def kit_json_command(
    name: str,
    results: list[type],
    error_type: type | None = None,
    exit_on_error: bool = True,  # NEW
    **click_kwargs: Any,
) -> Callable[[Callable[..., object]], click.Command]:
    """Decorator for kit CLI commands that output JSON.

    Automatically:
    - Passes Click context as first argument
    - Generates JSON schema documentation for --help
    - Handles JSON serialization of dataclass results
    - Sets exit code based on exit_on_error parameter
    """
    def decorator(func: Callable[..., object]) -> click.Command:
        @wraps(func)
        def wrapper(ctx: click.Context, *args: Any, **kwargs: Any) -> None:
            result = func(ctx, *args, **kwargs)

            # Output JSON
            if dataclasses.is_dataclass(result) and not isinstance(result, type):
                click.echo(json.dumps(dataclasses.asdict(result), indent=2))
            else:
                click.echo(json.dumps(result, indent=2))

            # Exit with error code if error result AND exit_on_error=True
            if exit_on_error and error_type and isinstance(result, error_type):
                raise SystemExit(1)

        # Build command with schema epilog AND pass_context
        cmd = click.command(
            name=name,
            cls=SchemaCommand,
            epilog=build_epilog(*results),
            **click_kwargs,
        )(click.pass_context(wrapper))

        return cmd

    return decorator
```

### Step 2: Migrate Commands

For each command:
1. Replace `@click.command(...)` + `@click.pass_context` with `@kit_json_command(...)`
2. Remove manual `json.dumps(asdict(result))` calls - just return the result
3. Remove manual `raise SystemExit(...)` for final return - decorator handles it
4. For graceful degradation commands, add `exit_on_error=False`

**Migration pattern for context-dependent command:**

Before:
```python
@click.command(
    name="mark-impl-ended",
    cls=SchemaCommand,
    epilog=build_epilog(MarkImplSuccess, MarkImplError),
)
@click.pass_context
def mark_impl_ended(ctx: click.Context) -> None:
    # ... logic ...
    if error:
        result = MarkImplError(...)
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)

    result = MarkImplSuccess(...)
    click.echo(json.dumps(asdict(result), indent=2))
```

After:
```python
@kit_json_command(
    name="mark-impl-ended",
    results=[MarkImplSuccess, MarkImplError],
    error_type=MarkImplError,
    exit_on_error=False,  # Graceful degradation
)
def mark_impl_ended(ctx: click.Context) -> MarkImplSuccess | MarkImplError:
    # ... logic ...
    if error:
        return MarkImplError(...)

    return MarkImplSuccess(...)
```

**Migration pattern for simple command (no context needed):**

Before:
```python
@click.command(
    name="find-project-dir",
    cls=SchemaCommand,
    epilog=build_epilog(ProjectInfo, ProjectError),
)
def find_project_dir(...) -> None:
    result = find_project_info(path)
    click.echo(json.dumps(asdict(result), indent=2))
    if isinstance(result, ProjectError):
        raise SystemExit(1)
```

After:
```python
@kit_json_command(
    name="find-project-dir",
    results=[ProjectInfo, ProjectError],
    error_type=ProjectError,
)
def find_project_dir(ctx: click.Context, ...) -> ProjectInfo | ProjectError:
    # ctx available but not used
    return find_project_info(path)
```

### Step 3: Commands to Migrate

1. **find-project-dir.py** - No context, exit_on_error=True
2. **parse-issue-reference.py** - Already done, just add ctx parameter
3. **mark-impl-started.py** - Context needed, exit_on_error=False
4. **mark-impl-ended.py** - Context needed, exit_on_error=False
5. **post-start-comment.py** - Context needed, exit_on_error=False
6. **post-pr-comment.py** - Context needed, exit_on_error=False
7. **update-dispatch-info.py** - Context needed, exit_on_error=False
8. **get-pr-commit-message.py** - No context, exit_on_error=True

### Step 4: Update Tests

Update existing tests to account for:
- New ctx parameter in function signatures
- Changed error handling behavior
- Decorator behavior changes

### Step 5: Update Documentation

Update `packages/dot-agent-kit/docs/KIT_CLI_COMMANDS.md` to document:
- New decorator signature with `exit_on_error` parameter
- Standard pattern for context-dependent commands
- Migration guide from manual pattern

## Files to Modify

**Core:**
- `packages/dot-agent-kit/src/dot_agent_kit/cli/schema.py` - Enhance decorator

**ERK Kit Commands:**
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/parse_issue_reference.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/find_project_dir.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/mark_impl_started.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/mark_impl_ended.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/post_start_comment.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/post_pr_comment.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/update_dispatch_info.py`

**GT Kit Commands:**
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/get_pr_commit_message.py`

**Tests:**
- `packages/dot-agent-kit/tests/unit/cli/test_schema.py`

**Docs:**
- `packages/dot-agent-kit/docs/KIT_CLI_COMMANDS.md`

## Edge Cases

1. **Early returns with errors:** Commands that have multiple error paths should use the new pattern - just return the error dataclass early. The decorator handles serialization and exit codes.

2. **Complex control flow (mark_impl_started/ended):** These commands have many try/except blocks. The migration will simplify these by making each error case just return an error dataclass.

3. **Commands that don't need context:** They still get `ctx` as first parameter but can ignore it. This maintains consistency.