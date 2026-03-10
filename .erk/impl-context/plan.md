# Plan: Create `erk json objective view` and `erk json objective check` machine commands

Part of Objective #9009, Node 3.2

## Context

The "best-of-both-worlds" machine command architecture (PR #9132) separates human CLI commands from machine-readable JSON commands. Human commands live at `erk <path>` with rich output; machine commands live at `erk json <path>` with structured JSON I/O via `@machine_command`.

Currently, `erk objective view` and `erk objective check` have `--json-output` flags inline — the legacy pattern. This plan migrates them to the new architecture: extract shared operations into `operation.py`, create thin `json_cli.py` machine adapters, and register them under `erk json objective view/check`.

## Implementation

### Phase 1: Extract `objective view` operation

**Create `src/erk/cli/commands/objective/view/operation.py`**

Extract from `view_cmd.py`:
- `ObjectiveViewRequest` frozen dataclass: `identifier: str | None = None` (optional, infers from branch)
- `ObjectiveViewResult` frozen dataclass with fields: `issue_number`, `phases` (serialized), `graph_nodes`, `unblocked`, `pending_unblocked`, `next_node`, `is_complete`, `summary`. Include `to_json_dict()` matching the current `_display_json` output shape.
- `run_objective_view()` function: the shared logic from `view_objective()` that fetches the issue, validates the label, parses the roadmap, builds the graph, and returns `ObjectiveViewResult | MachineCommandError`.

**Refactor `view_cmd.py` → `src/erk/cli/commands/objective/view/cli.py`**

Move the human command to the new location. It imports from `operation.py` and calls `run_objective_view()`, then renders with Rich tables (all existing `_format_*` and display functions move here).

**Create `src/erk/cli/commands/objective/view/json_cli.py`**

Thin machine adapter following the pr/view pattern:
```python
@machine_command(request_type=ObjectiveViewRequest, output_types=(ObjectiveViewResult,))
@click.command("view")
@click.pass_obj
def json_objective_view(ctx, *, request):
    return run_objective_view(ctx, request, repo_id=...)
```

No `@mcp_exposed` yet — that's node 3.3.

### Phase 2: Extract `objective check` operation

**Create `src/erk/cli/commands/objective/check/operation.py`**

Extract from `check_cmd.py`:
- `ObjectiveCheckRequest` frozen dataclass: `identifier: str` (required), `allow_legacy: bool = False`
- `ObjectiveCheckResult` frozen dataclass wrapping `ObjectiveValidationSuccess` data with `to_json_dict()` matching current `_output_json` shape.
- `run_objective_check()`: calls existing `validate_objective()` and wraps the result.

Keep `validate_objective()`, `ObjectiveValidationSuccess`, `ObjectiveValidationError`, and the `_check_*` helper functions in a shared module (either keep them in `check_cmd.py` and import, or move to `check/validation.py`). Prefer moving to `check/validation.py` since it's pure logic.

**Refactor `check_cmd.py` → `src/erk/cli/commands/objective/check/cli.py`**

Human command that calls `run_objective_check()` and renders `[PASS]/[FAIL]` output.

**Create `src/erk/cli/commands/objective/check/json_cli.py`**

Thin machine adapter:
```python
@machine_command(request_type=ObjectiveCheckRequest, output_types=(ObjectiveCheckResult,))
@click.command("check")
@click.pass_obj
def json_objective_check(ctx, *, request):
    return run_objective_check(ctx, request, repo_id=...)
```

### Phase 3: Register in JSON command tree

**Create `src/erk/cli/commands/json/objective/__init__.py`**
```python
@click.group("objective")
def json_objective_group():
    """Machine-readable objective commands."""
    pass

json_objective_group.add_command(json_objective_view, name="view")
json_objective_group.add_command(json_objective_check, name="check")
```

**Update `src/erk/cli/commands/json/__init__.py`**
```python
json_group.add_command(json_objective_group, name="objective")
```

**Update `src/erk/cli/commands/objective/__init__.py`**

Update imports from new subpackage locations (`view/cli.py`, `check/cli.py`).

### Phase 4: Deprecate `--json-output` flags

Keep the `--json-output` flags on the human commands for backwards compatibility during transition, but have them emit a deprecation warning pointing to `erk json objective view/check`. The flags delegate to the same `run_*` operation.

## Key Files

| File | Action |
|------|--------|
| `src/erk/cli/commands/objective/view_cmd.py` | Delete (split into view/ subpackage) |
| `src/erk/cli/commands/objective/check_cmd.py` | Delete (split into check/ subpackage) |
| `src/erk/cli/commands/objective/view/__init__.py` | Create (empty) |
| `src/erk/cli/commands/objective/view/operation.py` | Create (request/result/run) |
| `src/erk/cli/commands/objective/view/cli.py` | Create (human command) |
| `src/erk/cli/commands/objective/view/json_cli.py` | Create (machine adapter) |
| `src/erk/cli/commands/objective/check/__init__.py` | Create (empty) |
| `src/erk/cli/commands/objective/check/validation.py` | Create (validation logic) |
| `src/erk/cli/commands/objective/check/operation.py` | Create (request/result/run) |
| `src/erk/cli/commands/objective/check/cli.py` | Create (human command) |
| `src/erk/cli/commands/objective/check/json_cli.py` | Create (machine adapter) |
| `src/erk/cli/commands/json/objective/__init__.py` | Create (json group) |
| `src/erk/cli/commands/json/__init__.py` | Update (add objective group) |
| `src/erk/cli/commands/objective/__init__.py` | Update imports |

## Patterns to Follow

- **Decorator order**: `@machine_command` > `@click.command` > `@click.pass_obj` (no `@mcp_exposed` — that's node 3.3)
- **Repo resolution**: Use `resolve_owner_repo(ctx, target_repo=None)` in json_cli.py (same as pr/view/json_cli.py)
- **Error returns**: Return `MachineCommandError(error_type=..., message=...)` not exceptions
- **Result serialization**: Implement `to_json_dict()` on result dataclasses
- **Request defaults**: Use defaults for optional fields (e.g., `identifier: str | None = None`)
- **No `@mcp_exposed`**: That's explicitly node 3.3, not this node

## Verification

1. `erk json objective view --schema` returns valid input/output schema
2. `echo '{"identifier": "9009"}' | erk json objective view` returns JSON matching current `erk objective view 9009 --json-output`
3. `erk json objective check --schema` returns valid schema
4. `echo '{"identifier": "9009"}' | erk json objective check` returns JSON matching current `erk objective check 9009 --json-output`
5. `erk objective view 9009` still works (human output unchanged)
6. `erk objective check 9009` still works (human output unchanged)
7. Run existing tests: `pytest tests/ -k objective`
8. Run ty and ruff checks
