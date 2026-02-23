---
title: PlanRowData Field Reference
read_when:
  - "writing command availability predicates"
  - "understanding what data is available for TUI commands"
  - "checking which PlanRowData fields are nullable"
last_audited: "2026-02-23 00:15 PT"
audit_result: edited
---

# PlanRowData Field Reference

Quick reference for writing command availability predicates and understanding
`PlanRowData` usage patterns.

**Field definitions live in code:** See `src/erk/tui/data/types.py` for the
complete field list with types, nullability, and descriptions.

## Common Availability Patterns

### Check if PR exists

```python
is_available=lambda ctx: ctx.row.pr_number is not None
```

### Check if plan URL exists

```python
is_available=lambda ctx: ctx.row.plan_url is not None
```

### Check if worktree exists locally

```python
is_available=lambda ctx: ctx.row.exists_locally
```

### Check if workflow run exists

```python
is_available=lambda ctx: ctx.row.run_url is not None
```

### Compound conditions

```python
# PR exists AND worktree exists locally
is_available=lambda ctx: ctx.row.pr_number is not None and ctx.row.exists_locally

# Either PR or plan URL exists
is_available=lambda ctx: bool(ctx.row.pr_url or ctx.row.plan_url)
```

### Always available

```python
is_available=lambda _: True
```

## Testing with make_plan_row()

The test helper `make_plan_row()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py` creates `PlanRowData` instances with sensible defaults. Override only the fields you need:

```python
from erk_shared.gateway.plan_data_provider.fake import make_plan_row

# Minimal row
row = make_plan_row(123, "Test Plan")

# With PR
row = make_plan_row(123, "Test", pr_number=456, pr_url="https://...")

# With PR and comment counts (resolved, total)
row = make_plan_row(123, "Test", pr_number=456, comment_counts=(3, 5))

# With local worktree
row = make_plan_row(123, "Test", worktree_name="feature-123", exists_locally=True)

# With workflow run
row = make_plan_row(123, "Test", run_url="https://github.com/.../runs/789")
```

## Related Topics

- [adding-commands.md](adding-commands.md) - How to add new TUI commands
- [architecture.md](architecture.md) - Overall TUI architecture
