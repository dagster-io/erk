---
title: Issue Reference Flow
read_when:
  - "issue references not appearing in PRs"
  - "debugging 'Closes #N' in PR body"
  - "working with plan-ref.json"
  - "closing reference lost after erk pr submit"
last_audited: "2026-02-16 14:05 PT"
audit_result: clean
---

# Issue Reference Flow

This document describes how issue references flow through the erk system, from creation to consumption in PR bodies.

## Creation

The `save_plan_ref()` function in `erk_shared/impl_folder.py` writes to `plan-ref.json`.

Parameters are keyword-only after `impl_dir`:

See `save_plan_ref()` in
[`packages/erk-shared/src/erk_shared/impl_folder.py`](../../../packages/erk-shared/src/erk_shared/impl_folder.py)
for the full signature. Key points: all parameters after `impl_dir` are keyword-only (`provider`, `plan_id`, `url`, `labels`, `objective_id`).

Called by:

- `create_worker_impl_folder()` - For remote implementation
- `setup-impl-from-issue` exec command - For local implementation

## Reading

Three functions in `erk_shared/impl_folder.py`:

- `has_plan_ref(impl_dir)` - Checks if plan-ref.json (or legacy issue.json) exists
- `read_plan_ref(impl_dir)` - Returns `PlanRef` dataclass (with legacy fallback)
- `validate_plan_linkage(impl_dir, branch_name)` - Validates branch name matches plan reference

`read_plan_ref()` implements backward compatibility: tries `plan-ref.json` first, falls back to legacy `issue.json` transparently.

## Consumers

Commands that should auto-read from `.impl/plan-ref.json`:

| Command              | Auto-reads? | Purpose                     |
| -------------------- | ----------- | --------------------------- |
| `finalize.py`        | Yes         | Adds 'Closes #N' to PR body |
| `get-pr-body-footer` | Yes         | Generates PR footer text    |

## Fallback: Extracting from Existing PR Body

When `.impl/plan-ref.json` is missing during finalize, the system uses a fallback mechanism to preserve closing references:

1. **Fetch current PR body** from GitHub
2. **Extract footer** (content after `---` delimiter)
3. **Parse closing reference** patterns: `Closes #N` or `Closes owner/repo#N`
4. **Use extracted reference** when rebuilding the PR body

**Precedence:**

| Source                 | Priority    | When Used                         |
| ---------------------- | ----------- | --------------------------------- |
| `.impl/plan-ref.json`  | 1 (highest) | Authoritative source when present |
| `.impl/issue.json`     | 2           | Legacy fallback (read_plan_ref)   |
| Extracted from PR body | 3           | Fallback when neither file exists |
| None                   | 4           | No closing reference added        |

**Why This Matters:**

Running `erk pr submit` multiple times can trigger finalize, which completely rebuilds the PR body. Without this fallback, closing references would be lost if:

- `.impl/plan-ref.json` was deleted between submit runs
- `.impl/` directory doesn't exist (auto-repair only runs if directory exists)
- Issue was manually added to PR body (not stored in plan-ref.json)

**Implementation:** See `extract_closing_reference()` in `erk_shared/gateway/github/pr_footer.py`.

## Anti-Pattern

**Don't require explicit `--issue-number` when `.impl/plan-ref.json` exists.**

This creates unnecessary coupling between callers and the issue reference system. Commands should transparently read from the standard location.

## Data Flow Diagram

```
┌─────────────────────┐
│ create_worker_impl  │
│ or setup-impl       │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ .impl/plan-ref.json │
│ {                   │
│   "provider": "github",│
│   "plan_id": "123", │
│   "url": "..."      │
│ }                   │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ finalize.py         │
│ get-pr-body-footer  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ PR Body:            │
│ "Closes #123"       │
└─────────────────────┘
```

## Related Topics

- [PR Finalization Paths](pr-finalization-paths.md) - Local vs remote PR submission
- [PlanRef Architecture](plan-ref-architecture.md) - PlanRef dataclass and provider-agnostic design
