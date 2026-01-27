# Consolidated Documentation Plan: Git Subgateway Extraction Phases 3-7

> **Consolidates:** #6175, #6183, #6185, #6187, #6188

## Source Plans

| #    | Title                                  | Items Merged |
| ---- | -------------------------------------- | ------------ |
| 6175 | Phase 3 - Remote Subgateway Extraction | 7 items      |
| 6183 | Phase 4 - Commit Subgateway Extraction | 10 items     |
| 6185 | Phase 5 - Status Subgateway Extraction | 4 items      |
| 6187 | Phase 6 - Rebase Subgateway Extraction | 5 items      |
| 6188 | Phase 7 - Tag Subgateway Extraction    | 6 items      |

## Context

Phases 3-7 of the Gateway Decomposition Initiative (#6169) systematically extracted Git operations into dedicated subgateways. All code implementations are **complete and merged**:

- Phase 3: GitRemoteOps (PR #6171) - 6 methods
- Phase 4: GitCommitOps (PR #6180) - 8 methods
- Phase 5: GitStatusOps (PR #6179) - 5 methods
- Phase 6: GitRebaseOps (PR #6182) - 4 methods
- Phase 7: GitTagOps (PR #6186) - 3 methods

**Critical Finding:** Documentation is almost entirely missing. The gateway-inventory.md only documents GitBranchOps and Worktree - none of the 5 newly extracted subgateways are documented.

## Investigation Findings

### What Exists

- `docs/learned/architecture/gateway-inventory.md` - has Sub-Gateways section but outdated
- `docs/learned/architecture/flatten-subgateway-pattern.md` - comprehensive pattern doc with GitBranchOps example
- `docs/learned/architecture/gateway-abc-implementation.md` - documents 5-layer pattern

### What's Missing (Overlap Identified)

1. **Gateway Inventory entries** - All 5 phases need entries (highest overlap)
2. **Phase timeline document** - All phases reference needing this
3. **Tripwires for old-style access** - All phases need warnings about moved methods
4. **Read-only vs mutable subgateway distinction** - Phases 5, 6 need this
5. **Callback DI pattern documentation** - Phase 6 specifically uses this

## Implementation Steps

### Step 1: Update Gateway Inventory (HIGH - addresses all 5 plans)

**File:** `docs/learned/architecture/gateway-inventory.md`

Add 5 new subsections under "## Sub-Gateways" after line 372 (after GraphiteBranchOps):

```markdown
### GitRemoteOps (`git/remote_ops/`)

Git remote operations extracted from the main Git gateway (Phase 3 of #6169).

**Key Methods**:

- `fetch_branch()`: Fetch specific branch from remote
- `pull_branch()`: Pull with optional fast-forward-only flag
- `fetch_pr_ref()`: Fetch GitHub PR references
- `push_to_remote()`: Push with upstream tracking and force options
- `pull_rebase()`: Pull with rebase integration
- `get_remote_url()`: Query remote repository URLs

**Fake Features**: Mutation tracking for fetched/pushed branches, exception injection.

**Access Pattern**: `git.remote.method_name()` - exposed via property on main Git gateway.

### GitCommitOps (`git/commit_ops/`)

Git commit operations extracted from the main Git gateway (Phase 4 of #6169).

**Key Methods**:

- Mutations: `stage_files()`, `commit()`, `add_all()`, `amend_commit()`
- Queries: `get_commit_message()`, `get_recent_commits()`, `get_commits_since_base()`, `worktree_is_dirty()`, `count_commits_ahead()`

**Fake Features**: `CommitRecord` frozen dataclass for mutation tracking, staging semantics (accumulate/clear).

**Access Pattern**: `git.commit.method_name()`

### GitStatusOps (`git/status_ops/`)

Git status query operations extracted from the main Git gateway (Phase 5 of #6169).

**Purpose**: Separates read-only status queries from mutable operations.

**Key Methods**:

- `has_staged_changes()`: Check for staged changes
- `has_uncommitted_changes()`: Check for any uncommitted changes
- `get_file_status()`: Returns (staged, modified, untracked) file lists
- `check_merge_conflicts()`: Merge conflict detection
- `get_conflicted_files()`: List files with conflict markers

**Note**: All query-only; no mutations. DryRun and Printing wrappers are simple pass-through delegators.

**Access Pattern**: `git.status.method_name()`

### GitRebaseOps (`git/rebase_ops/`)

Git rebase operations extracted from the main Git gateway (Phase 6 of #6169).

**Key Methods**:

- `rebase_onto()`: Rebase current branch onto target ref
- `rebase_continue()`: Continue in-progress rebase
- `rebase_abort()`: Abort in-progress rebase
- `is_rebase_in_progress()`: Check if rebase in progress

**Fake Features**: In-memory rebase state, mutation tracking, configurable results/exceptions, `link_mutation_tracking()` method.

**Note**: Uses callback DI pattern - RealGitRebaseOps receives `get_git_common_dir` and `get_conflicted_files` as Callables.

**Access Pattern**: `git.rebase.method_name()`

### GitTagOps (`git/tag_ops/`)

Git tag operations extracted from the main Git gateway (Phase 7 of #6169).

**Key Methods**:

- `tag_exists()`: Query operation - check if a tag exists
- `create_tag()`: Create an annotated git tag
- `push_tag()`: Push a tag to a remote repository

**Fake Features**: In-memory tag state with linked mutation tracking. Parent FakeGit shares `_created_tags` and `_pushed_tags` containers with FakeGitTagOps.

**Access Pattern**: `git.tag.method_name()`
```

**Verification**: Search for all subgateways and confirm each has an entry.

---

### Step 2: Create Gateway Decomposition Phases Document (HIGH - addresses all plans)

**File:** `docs/learned/architecture/gateway-decomposition-phases.md` (CREATE)

```markdown
---
title: Gateway Decomposition Phases
read_when:
  - "understanding the gateway decomposition initiative"
  - "planning new subgateway extractions"
  - "reviewing architectural history"
---

# Gateway Decomposition Phases

Timeline of the systematic Git gateway decomposition (#6169).

## Overview

The monolithic Git gateway originally contained all git operations. This initiative decomposed it into focused subgateways, each responsible for a cohesive set of operations.

## Phase Timeline

| Phase   | Subgateway   | Operations Extracted                                                                                      | PR        | Status   |
| ------- | ------------ | --------------------------------------------------------------------------------------------------------- | --------- | -------- |
| Phase 2 | GitBranchOps | create_branch, delete_branch, checkout_branch, checkout_detached, create_tracking_branch                  | (earlier) | Complete |
| Phase 3 | GitRemoteOps | fetch_branch, pull_branch, fetch_pr_ref, push_to_remote, pull_rebase, get_remote_url                      | #6171     | Complete |
| Phase 4 | GitCommitOps | stage_files, commit, add_all, amend_commit, get_commit_message, get_recent_commits, etc.                  | #6180     | Complete |
| Phase 5 | GitStatusOps | has_staged_changes, has_uncommitted_changes, get_file_status, check_merge_conflicts, get_conflicted_files | #6179     | Complete |
| Phase 6 | GitRebaseOps | rebase_onto, rebase_continue, rebase_abort, is_rebase_in_progress                                         | #6182     | Complete |
| Phase 7 | GitTagOps    | tag_exists, create_tag, push_tag                                                                          | #6186     | Complete |

## Pattern

Each phase follows the same extraction pattern:

1. Create subgateway directory with 5-layer structure (abc, real, fake, dry_run, printing)
2. Move method implementations to new files
3. Add property to parent gateway (all 5 layers)
4. Migrate callsites to new property path (e.g., `git.method()` → `git.subgateway.method()`)
5. Remove methods from parent gateway
6. Document in gateway inventory

## Subgateway Variants

| Variant          | Example                    | DryRun Behavior                   | Printing Behavior               |
| ---------------- | -------------------------- | --------------------------------- | ------------------------------- |
| Mutation-focused | GitBranchOps, GitTagOps    | No-op, return success             | Log then delegate               |
| Query-only       | GitStatusOps               | Pass-through delegate             | Pass-through delegate           |
| Mixed            | GitRemoteOps, GitCommitOps | Mutations no-op, queries delegate | Mutations log, queries delegate |

## Related

- [Flatten Subgateway Pattern](flatten-subgateway-pattern.md)
- [Gateway Inventory](gateway-inventory.md)
- [Gateway ABC Implementation](gateway-abc-implementation.md)
```

**Verification**: Check that all phases are listed with correct PR numbers.

---

### Step 3: Add Tripwires for Subgateway Migration (MEDIUM - addresses phases 3-7)

**File:** `docs/learned/tripwires-index.md`

Add new category entry:

```markdown
| When migrating git method calls after subgateway extraction | Search for old-style `git.method()` calls and update to `git.subgateway.method()` | `architecture/gateway-decomposition-phases.md` |
```

**File:** `docs/learned/architecture/tripwires.md`

Add new section before "## GitBranchOps Tripwires":

```markdown
## Subgateway Migration Tripwires

### Before calling methods that were extracted to subgateways

**CRITICAL:** The following methods have been moved from the Git ABC to subgateways:

| Old API                    | New API                           | Phase   |
| -------------------------- | --------------------------------- | ------- |
| `git.fetch_branch()`       | `git.remote.fetch_branch()`       | Phase 3 |
| `git.push_to_remote()`     | `git.remote.push_to_remote()`     | Phase 3 |
| `git.commit()`             | `git.commit.commit()`             | Phase 4 |
| `git.stage_files()`        | `git.commit.stage_files()`        | Phase 4 |
| `git.has_staged_changes()` | `git.status.has_staged_changes()` | Phase 5 |
| `git.rebase_onto()`        | `git.rebase.rebase_onto()`        | Phase 6 |
| `git.tag_exists()`         | `git.tag.tag_exists()`            | Phase 7 |
| `git.create_tag()`         | `git.tag.create_tag()`            | Phase 7 |

Calling the old API will raise `AttributeError`. Always use the subgateway property.
```

**Verification**: Grep for any remaining old-style calls in codebase.

---

### Step 4: Update Flatten Subgateway Pattern with Read-Only Note (MEDIUM - Phase 5)

**File:** `docs/learned/architecture/flatten-subgateway-pattern.md`

Add new section after "## Example: Git Branch Operations":

```markdown
## Read-Only Subgateways

When a subgateway contains only query operations (no mutations), the DryRun and Printing wrapper layers can be simplified to pure pass-through delegation.

**Example:** GitStatusOps contains only query methods (`has_staged_changes`, `get_file_status`, etc.), so:

- `DryRunGitStatusOps` simply delegates to the wrapped implementation
- `PrintingGitStatusOps` simply delegates without logging

There's no special dry-run behavior needed because queries have no side effects to suppress.

See [Gateway Decomposition Phases](gateway-decomposition-phases.md) for the full list of subgateway variants.
```

**Verification**: Check that the read-only pattern is mentioned.

---

### Step 5: Document Callback DI Pattern (LOW - Phase 6 specific)

**File:** `docs/learned/architecture/gateway-abc-implementation.md`

Add new section after "## Time Injection for Retry-Enabled Gateways":

````markdown
## Callback Injection for Subgateway Dependencies

When a subgateway needs to call methods from sibling subgateways or the parent gateway, use callback injection to avoid circular imports.

### Pattern

Pass parent methods as `Callable` parameters in the constructor:

```python
class RealGitRebaseOps(GitRebaseOps):
    def __init__(
        self,
        get_git_common_dir: Callable[[Path], Path],
        get_conflicted_files: Callable[[Path], list[str]],
    ) -> None:
        self._get_git_common_dir = get_git_common_dir
        self._get_conflicted_files = get_conflicted_files
```
````

### Why Not Direct Imports?

Direct imports would create circular dependencies:

- `rebase_ops/real.py` imports `status_ops/abc.py`
- `status_ops/real.py` imports common types
- Common types import `git/abc.py`
- `git/abc.py` imports `rebase_ops/abc.py`

Callback injection breaks this cycle by deferring the dependency to runtime.

### Reference Implementation

`RealGitRebaseOps` in `packages/erk-shared/src/erk_shared/gateway/git/rebase_ops/real.py` demonstrates this pattern.

````

**Verification**: Check that callback DI is documented.

---

### Step 6: Update docs/learned/index.md (LOW - housekeeping)

**File:** `docs/learned/index.md`

Add entry for new document:

```markdown
| gateway-decomposition-phases.md | architecture | Timeline of Git gateway decomposition phases 3-7 | Understanding gateway extraction history |
````

**Verification**: Check that index includes new doc.

---

## Attribution

Items by source plan:

- **#6175 (Phase 3 Remote)**: Steps 1, 2, 3
- **#6183 (Phase 4 Commit)**: Steps 1, 2, 3
- **#6185 (Phase 5 Status)**: Steps 1, 2, 4
- **#6187 (Phase 6 Rebase)**: Steps 1, 2, 5
- **#6188 (Phase 7 Tag)**: Steps 1, 2, 3

## Deferred Items

The following items from individual plans are **NOT included** in this consolidated plan because they would create fragmented documentation. They could be addressed in future work:

1. **Individual case study documents** (e.g., phase-7-tag-extraction-case-study.md) - The decomposition phases document serves as a unified reference instead
2. **git-gateway-api.md** - Gateway inventory provides sufficient API documentation
3. **fakes-commit-ops.md** - CommitRecord pattern can be added to fake-driven-testing skill if needed
4. **LibCST callsite migration pattern** - Existing libcst-systematic-imports.md could be extended, but not high priority

## Verification

After implementation:

1. `grep -r "GitRemoteOps\|GitCommitOps\|GitStatusOps\|GitRebaseOps\|GitTagOps" docs/learned/architecture/gateway-inventory.md` should find all 5
2. `ls docs/learned/architecture/gateway-decomposition-phases.md` should exist
3. `grep "git.remote.fetch_branch" docs/learned/architecture/tripwires.md` should find migration tripwire
4. `grep "Read-Only" docs/learned/architecture/flatten-subgateway-pattern.md` should find new section
