# Extraction Plan: Local Plans and Session Store Documentation

## Objective

Add documentation for the local plans system (`~/.claude/plans/`) and update session store testing docs to include plan functionality.

## Source Information

- Session ID: f779cf08-a578-4e6d-8e65-ecc9702d3e1e
- Related implementation: Issue #2793 (Add Local Plan Abstraction to ClaudeCodeSessionStore)

## Documentation Items

### Item 1: Local Plans Architecture Documentation

**Type:** Category A (Learning Gap)
**Location:** `docs/agent/architecture/local-plans.md`
**Action:** Create new document
**Priority:** Medium

**Content:**

```markdown
---
title: Local Plans Architecture
read_when:
  - "working with ~/.claude/plans/ directory"
  - "understanding plan file discovery"
  - "session-scoped plan lookup"
---

# Local Plans Architecture

Claude Code stores plans in `~/.claude/plans/` as markdown files. The erk codebase provides abstractions for accessing these plans.

## Directory Structure
```

~/.claude/plans/
├── serene-juggling-cupcake.md # Plan files named by slug
├── azure-dancing-elephant.md
└── ...

````

Plan files are named using slugs (adjective-verb-noun patterns) and contain markdown content.

## Plan Access via ClaudeCodeSessionStore

The `ClaudeCodeSessionStore` ABC provides plan access through `get_latest_plan()`:

```python
plan_content = session_store.get_latest_plan(
    project_cwd=cwd,
    session_id=session_id,  # Optional: for session-scoped lookup
)
````

### Lookup Priority

1. **Session-scoped lookup** (when `session_id` provided): Searches session logs for slug fields, returns matching plan
2. **mtime fallback**: Returns most recently modified `.md` file in plans directory

### Testing with Fakes

Use `FakeClaudeCodeSessionStore` with the `plans` parameter:

```python
fake_store = FakeClaudeCodeSessionStore(
    plans={"my-plan-slug": "# Plan Title\n\n- Step 1"},
)

# get_latest_plan() returns the fake plan content
plan = fake_store.get_latest_plan(cwd)
```

## Related

- [Session Store Testing](../testing/session-store-testing.md) - Testing patterns for session store
- Implementation: `erk_shared.extraction.claude_code_session_store`

```

### Item 2: Update Session Store Testing Doc

**Type:** Category B (Teaching Gap)
**Location:** `docs/agent/testing/session-store-testing.md`
**Action:** Update existing document
**Priority:** High (depends on #2793 implementation)

**Changes to add:**

After the "Key Methods" table, add new row:
```

| `get_latest_plan(project_cwd, session_id=None)` | Returns plan content from fake plans |

````

Add new section after "Testing Flag Overrides":

```markdown
## Testing Plan Access

The `FakeClaudeCodeSessionStore` supports fake plan data via the `plans` parameter:

### Basic Plan Setup

```python
fake_store = FakeClaudeCodeSessionStore(
    plans={"my-feature": "# My Feature Plan\n\n- Step 1\n- Step 2"},
)

# Returns plan content
plan = fake_store.get_latest_plan(tmp_path)
assert plan == "# My Feature Plan\n\n- Step 1\n- Step 2"
````

### Session-Scoped Plan Lookup

When `session_id` matches a key in `plans`, that specific plan is returned:

```python
fake_store = FakeClaudeCodeSessionStore(
    plans={
        "session-abc": "# Plan for Session ABC",
        "session-xyz": "# Plan for Session XYZ",
    },
)

# Returns specific plan when session_id matches
plan = fake_store.get_latest_plan(tmp_path, session_id="session-abc")
assert "Session ABC" in plan
```

### Testing "No Plan Found"

```python
fake_store = FakeClaudeCodeSessionStore(plans={})  # Empty plans
plan = fake_store.get_latest_plan(tmp_path)
assert plan is None
```

### Replacing Monkeypatch Patterns

Before (monkeypatch approach):

```python
@pytest.fixture
def plans_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    plans = tmp_path / ".claude" / "plans"
    plans.mkdir(parents=True)
    monkeypatch.setattr(
        "some.module.get_plans_dir",
        lambda: plans,
    )
    return plans

def test_something(plans_dir: Path) -> None:
    (plans_dir / "test.md").write_text("# Plan")
    # ...
```

After (fake store approach):

```python
def test_something() -> None:
    fake_store = FakeClaudeCodeSessionStore(
        plans={"test": "# Plan"},
    )
    result = runner.invoke(
        my_command,
        obj=DotAgentContext.for_test(session_store=fake_store),
    )
    # ...
```

````

Update "Related Topics" section to add:
```markdown
- [Local Plans Architecture](../architecture/local-plans.md) - How the local plans system works
````

## Implementation Notes

- Item 2 depends on implementation of issue #2793
- Both items should be implemented together after #2793 is merged
