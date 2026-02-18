# Plan: Fix broken links in README.md

Part of Objective #7457, Node 1.1

## Context

README.md contains 7 broken links that point to directory/file names from an earlier documentation structure. The docs were reorganized (e.g., `getting-started/` → `tutorials/`, `concepts/` → `topics/`) but the README was never updated to match. One CLI command name is also stale.

## File to Modify

`README.md` (single file, all changes)

## Changes

### 1. Fix `TAO.md` path (line 7)

- **Current:** `[The TAO of erk](TAO.md)`
- **Fixed:** `[The TAO of erk](docs/TAO.md)`

### 2. Fix tutorial link (line 24)

- **Current:** `[Your First Plan](docs/getting-started/first-plan.md)`
- **Fixed:** `[Your First Plan](docs/tutorials/first-plan.md)`

### 3. Fix command name (line 45)

- **Current:** `erk pr land`
- **Fixed:** `erk land`

### 4. Fix workflow link (line 48)

- **Current:** `[The Workflow](docs/concepts/the-workflow.md)`
- **Fixed:** `[The Workflow](docs/topics/the-workflow.md)`

### 5. Fix Documentation table (lines 52-58) — 4 broken directory paths + descriptions

| Current | Fixed |
|---------|-------|
| `[Getting Started](docs/getting-started/)` — Setup, installation, first tutorial | `[Tutorials](docs/tutorials/)` — Setup, installation, first plan tutorial |
| `[Concepts](docs/concepts/)` — Worktrees, stacked PRs, plan mode | `[Topics](docs/topics/)` — Worktrees, stacked PRs, plan mode |
| `[Guides](docs/guides/)` — Workflows for common tasks | `[How-to Guides](docs/howto/)` — Workflows for common tasks |
| `[Reference](docs/reference/)` — Commands, configuration, file locations | `[Reference](docs/ref/)` — Commands, configuration, file locations |
| `[Troubleshooting](docs/troubleshooting/)` — Common issues and solutions | `[FAQ](docs/faq/)` — Common questions and troubleshooting |

### Summary of all 8 fixes

1. `TAO.md` → `docs/TAO.md`
2. `docs/getting-started/first-plan.md` → `docs/tutorials/first-plan.md`
3. `erk pr land` → `erk land` (command name)
4. `docs/concepts/the-workflow.md` → `docs/topics/the-workflow.md`
5. `docs/getting-started/` → `docs/tutorials/`
6. `docs/concepts/` → `docs/topics/`
7. `docs/guides/` → `docs/howto/`
8. `docs/reference/` → `docs/ref/`
9. `docs/troubleshooting/` → `docs/faq/`

## Verification

After applying changes, verify every link target exists:

```bash
# Check all referenced paths exist
test -f docs/TAO.md && echo OK || echo BROKEN
test -f docs/tutorials/first-plan.md && echo OK || echo BROKEN
test -f docs/topics/the-workflow.md && echo OK || echo BROKEN
test -d docs/tutorials/ && echo OK || echo BROKEN
test -d docs/topics/ && echo OK || echo BROKEN
test -d docs/howto/ && echo OK || echo BROKEN
test -d docs/ref/ && echo OK || echo BROKEN
test -d docs/faq/ && echo OK || echo BROKEN
```

Verify `erk land` is a valid command:

```bash
erk land --help
```