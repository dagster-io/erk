# Plan: Documentation Gaps from Extraction Plan Workflow Session

## Objective

Document Category A learning gaps discovered during the extraction plan workflow implementation session. Focus on exception chaining lint compliance and kit CLI JSON output patterns.

## Documentation Items

### Item 1: Exception Chaining and B904 Lint Compliance

**Type:** Update to existing agent doc
**Location:** `.claude/docs/dignified-python/dignified-python-core.md`
**Action:** Enhance the "Adding Context Before Re-raising" section
**Priority:** Medium

**Rationale:** During implementation, hit B904 lint error for `raise SystemExit(1)` inside an `except` block. The current doc shows the pattern but doesn't explain:
- B904 requires explicit exception chaining in except blocks
- When to use `from e` vs `from None`
- That this is a mandatory lint rule, not just a best practice

**Draft Content:**

Add after the existing "Adding Context Before Re-raising" example (around line 114):

```markdown
### Exception Chaining (B904 Lint Compliance)

**Ruff rule B904** requires explicit exception chaining when raising inside an `except` block. This prevents losing the original traceback.

```python
# ✅ CORRECT: Chain to preserve context
try:
    parse_config(path)
except ValueError as e:
    click.echo(json.dumps({"success": False, "error": str(e)}))
    raise SystemExit(1) from e  # Preserves traceback

# ✅ CORRECT: Explicitly break chain when intentional
try:
    fetch_from_cache(key)
except KeyError:
    # Original exception is not relevant to caller
    raise ValueError(f"Unknown key: {key}") from None

# ❌ WRONG: Missing exception chain (B904 violation)
try:
    parse_config(path)
except ValueError:
    raise SystemExit(1)  # Lint error: missing 'from e' or 'from None'
```

**When to use each:**
- `from e` - Preserve original exception for debugging
- `from None` - Intentionally suppress original (e.g., transforming exception type)
```

### Item 2: Kit CLI Command JSON Output Pattern

**Type:** Addition to existing agent doc
**Location:** `docs/agent/kits/cli-commands.md`
**Action:** Add new section on JSON output conventions
**Priority:** Low

**Rationale:** Multiple kit CLI commands (15+) follow a consistent JSON output pattern that isn't documented. New commands should follow this pattern.

**Draft Content:**

Add new section after "Command Loading and Naming Conventions":

```markdown
## JSON Output Pattern for Kit CLI Commands

Kit CLI commands that produce machine-readable output follow a consistent pattern:

### Success Response

```python
click.echo(json.dumps({
    "success": True,
    "issue_number": result.number,
    "issue_url": result.url,
    # ... operation-specific fields
}))
```

### Error Response

```python
click.echo(json.dumps({
    "success": False,
    "error": "Human-readable error message",
}))
raise SystemExit(1)  # Use exit code 1 for errors
```

### Pattern Details

1. **Always include `success` field** - Boolean indicating operation result
2. **Error uses `error` field** - Human-readable message for LLM to report
3. **Exit codes** - 0 for success, 1 for errors
4. **Use `click.echo()`** - Not `print()`, for Click integration
5. **Single JSON line** - No pretty-printing for machine parsing

### Example: Full Pattern

```python
@click.command(name="my-command")
def my_command() -> None:
    """Do something and report result."""
    if not valid_input:
        click.echo(json.dumps({
            "success": False,
            "error": "Invalid input provided",
        }))
        raise SystemExit(1)

    result = do_work()

    click.echo(json.dumps({
        "success": True,
        "result_id": result.id,
        "result_url": result.url,
    }))
```
```

## Implementation Steps

1. Read `.claude/docs/dignified-python/dignified-python-core.md`
2. Add B904 exception chaining section after line 114
3. Read `docs/agent/kits/cli-commands.md`
4. Add JSON output pattern section at end of file
5. Run `make fast-ci` to verify no formatting issues