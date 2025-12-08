---
title: PR Finalization Paths
read_when:
  - "debugging PR body content or issue closing"
  - "understanding how 'Closes #N' is added to PRs"
  - "working with remote implementation workflows"
  - "comparing local vs remote PR submission"
---

# PR Finalization Paths

The erk system has two distinct code paths for finalizing PRs: local (Graphite) and remote (GitHub Actions). Both paths should behave identically, but use different entry points.

## Local Path (Graphite)

**Entry point:** `finalize.py` in `erk-shared`

**Used when:** Running `gt ss` (Graphite stack submit) or local PR submission

**Issue reference:** Auto-reads from `.impl/issue.json` using `read_issue_reference(impl_dir)`

**Behavior:**

- Checks if `.impl/issue.json` exists via `has_issue_reference(impl_dir)`
- If present, reads issue number and adds `Closes #N` to PR body footer
- PR body is updated via GitHub API

**Code location:** `erk_shared/finalize.py`

## Remote Path (GitHub Actions)

**Entry point:** `.github/workflows/dispatch-erk-queue-git.yml` workflow

**Used when:** Running `erk submit` for remote implementation queue

**Issue reference:** Commands should auto-read from `.impl/issue.json` (copied to `.impl/` from `.worker-impl/`)

**Behavior:**

- Workflow copies `.worker-impl/` to `.impl/` before implementation
- Commands use `get-pr-body-footer` to generate PR body content
- PR body should include `Closes #N` if `.impl/issue.json` exists

**Code location:** `.github/workflows/dispatch-erk-queue-git.yml`

## Key Principle: Consistent Behavior

**MUST:** Both paths should produce identical results

**MUST:** Commands should auto-read from `.impl/issue.json` rather than requiring explicit `--issue-number` parameters

**MUST NOT:** Require callers to explicitly pass issue references when `.impl/issue.json` exists

## Common Pitfalls

### Missing 'Closes #N' in Remote PRs

**Symptom:** Local PRs have `Closes #N`, but remote PRs don't

**Root cause:** Commands in remote path not auto-reading from `.impl/issue.json`

**Fix:** Ensure all PR body generation commands check for `.impl/issue.json` and include issue reference in footer

### Inconsistent Footer Format

**Symptom:** Different footer formats between local and remote PRs

**Root cause:** Multiple implementations of footer generation logic

**Fix:** Centralize footer generation in `erk_shared/impl_folder.py` and use consistently

## Related Documentation

- [Implementation Folder Lifecycle](impl-folder-lifecycle.md) - Understanding `.impl/` vs `.worker-impl/`
- [Issue Reference Flow](issue-reference-flow.md) - How issue references are created and consumed
