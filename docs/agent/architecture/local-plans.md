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
├── serene-juggling-cupcake.md    # Plan files named by slug
├── azure-dancing-elephant.md
└── ...
```

Plan files are named using slugs (adjective-verb-noun patterns) and contain markdown content.

## Plan Access via ClaudeCodeSessionStore

The `ClaudeCodeSessionStore` ABC provides plan access through `get_latest_plan()`:

```python
plan_content = session_store.get_latest_plan(
    project_cwd=cwd,
    session_id=session_id,  # Optional: for session-scoped lookup
)
```

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
