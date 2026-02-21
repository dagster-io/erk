# Documentation Plan: Replace session gist archival with branch-based storage

## Context

This implementation replaced the gist-based session archival system with branch-based storage, representing a significant architectural simplification. Sessions are now stored on git branches (`session/{plan_id}`) instead of GitHub gists, eliminating authentication gaps, providing transparency in the GitHub UI, and leveraging existing git infrastructure.

The implementation touched 22 files with a net deletion of 533 lines (908 removed, 375 added), demonstrating consolidation rather than expansion. The agent worked through 7 session parts, systematically updating exec scripts, shared types, gateway ABCs, schema validation, and tests. Key challenges included the schema-first migration pattern (updating validators before callers), test rewrites for gateway changes (FakeGitHub to FakeGit), and platform-specific tool syntax (macOS sed, global vs npx prettier).

Documentation matters because future agents will encounter: (1) breaking CLI parameter changes (`--gist-url` to `--session-branch`), (2) removed gateway methods (`create_gist` no longer exists), (3) new session branch conventions, and (4) several non-obvious gotchas discovered during implementation (stash side effects, prettier version consistency, sed syntax).

## Raw Materials

PR #7757

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 26    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 5     |
| Potential tripwires (score 2-3)| 8     |
| Stale docs to clean up         | 2     |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action:

### 1. Gist Materials Interchange

**Location:** `docs/learned/architecture/gist-materials-interchange.md`
**Action:** DELETE_STALE or UPDATE_REFERENCES
**Phantom References:** May reference obsolete gist materials workflow from PR #7733
**Cleanup Instructions:** Verify if this doc is now historical. PR #7733 replaced gist transport for learn materials. If the entire doc describes the old gist workflow, add a deprecation notice or delete. If it contains still-relevant content, update to clarify that sessions no longer use gists.

### 2. GitHub Gist API Reference

**Location:** `docs/learned/architecture/github-gist-api.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** Technical reference for gist URL patterns no longer used for sessions
**Cleanup Instructions:** Keep the doc since gists may be used elsewhere in erk, but add a note clarifying that session storage no longer uses gists. The gist API reference remains valid for any other gist usage.

## Documentation Items

### HIGH Priority

#### 1. Session storage architecture shift

**Location:** `docs/learned/sessions/lifecycle.md`
**Action:** UPDATE (replace "Why Gist-Based Persistence Exists" section)
**Source:** [Impl] Parts 2-3, [PR #7757]

**Draft Content:**

```markdown
## Why Branch-Based Persistence Exists

Session logs are stored on git branches (`session/{plan_id}`) rather than external storage. This design provides:

1. **Transparency**: Session branches visible in GitHub UI at `.erk/session/`
2. **Git infrastructure reuse**: Leverages existing git operations (fetch, push, show)
3. **No authentication gaps**: Uses gh CLI for both write and read
4. **Automatic cleanup**: Learn pipeline deletes session branch after extraction
5. **Version control**: Sessions are part of git history, can be tracked/audited
6. **Idempotency**: Force-push allows clean re-implementation without branch accumulation

See `src/erk/cli/commands/exec/scripts/upload_session.py` for implementation.
```

---

#### 2. Session branch naming convention and lifecycle

**Location:** `docs/learned/sessions/lifecycle.md` (new subsection)
**Action:** CREATE
**Source:** [Impl] Parts 2-3

**Draft Content:**

```markdown
## Session Branch Conventions

### Branch Naming

Session branches follow the pattern: `session/{plan_id}`

Example: Plan #7757 stores sessions on branch `session/7757`

### File Location

Session JSONL files are stored at: `.erk/session/session-{session_id}.jsonl`

### Lifecycle

1. **Creation**: `upload-session` creates branch from `origin/master`, commits session file
2. **Force-push**: Re-implementation force-pushes to same branch (idempotent)
3. **Extraction**: Learn pipeline reads session from branch
4. **Cleanup**: Learn pipeline deletes branch after extracting to `learn/{plan_id}`

See `src/erk/cli/commands/exec/scripts/upload_session.py` for creation logic.
See `src/erk/cli/commands/exec/scripts/trigger_async_learn.py` for cleanup logic (grep: `cleanup_session_branch`).
```

---

#### 3. Plan-header schema migration (BREAKING CHANGE)

**Location:** `docs/learned/glossary.md` + `docs/learned/architecture/session-discovery.md` + `docs/learned/sessions/lifecycle.md`
**Action:** UPDATE (global find/replace)
**Source:** [Impl] Parts 3-4, [PR #7757]

**Draft Content:**

```markdown
## Plan-Header Session Fields

**Current field (as of PR #7757):**
- `last_session_branch`: Branch name where session JSONL is stored (e.g., `session/7757`)

**Removed fields:**
- `last_session_gist_url` (REMOVED)
- `last_session_gist_id` (REMOVED)

The schema constant `LAST_SESSION_BRANCH` replaces `LAST_SESSION_GIST_URL` and `LAST_SESSION_GIST_ID`.

See `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py` for schema definition.
```

---

#### 4. Gateway ABC breaking change: create_gist removed

**Location:** `docs/learned/architecture/tripwires.md` or `docs/learned/gateway/tripwires.md`
**Action:** UPDATE (add tripwire entry)
**Source:** [Impl] Part 4, [PR #7757]

**Draft Content:**

```markdown
## Removed Gateway Methods

### create_gist (Removed in PR #7757)

The `create_gist` method has been removed from the GitHub gateway ABC. Session storage now uses git branches instead.

**Impact:** Removed from 5 places:
- `abc.py` (abstract method + `GistCreated`, `GistCreateError` types)
- `real.py` (gh gist create wrapper)
- `fake.py` (tracking state and method)
- `dry_run.py` (stub implementation)
- `printing.py` (logging wrapper)

**Alternative:** Use branch-based storage via git gateway operations. No external consumers existed for `create_gist`.
```

---

#### 5. Schema-first migration pattern

**Location:** `docs/learned/architecture/schema-migrations.md`
**Action:** CREATE
**Source:** [Impl] Part 3

**Draft Content:**

```markdown
# Schema-First Migration Pattern

When migrating metadata fields that go through schema validation, the order of updates is critical.

## Required Order

1. **Schema constants** - Update `schemas.py` field names and validation rules
2. **Validation logic** - Update any custom validators
3. **Extractor functions** - Update `extract_*` functions in `plan_header.py`
4. **Dataclass fields** - Update field names in dataclasses (e.g., `SessionsForPlan`)
5. **API callers** - Update code that calls `update_metadata()` and extractors

## Why This Order Matters

Updating callers before schema causes validation errors. The `update_metadata()` function validates fields against the schema before writing. If callers pass new field names but schema still expects old names, validation fails.

## Example

PR #7757 migrated `last_session_gist_url` to `last_session_branch`:
1. Updated `LAST_SESSION_BRANCH` constant in schemas.py
2. Updated validators to expect the new field
3. Replaced `extract_plan_header_session_gist_url()` with `extract_plan_header_session_branch()`
4. Renamed `SessionsForPlan.last_session_gist_url` to `last_session_branch`
5. Updated callers in upload_session.py and get_learn_sessions.py

See `packages/erk-shared/src/erk_shared/gateway/github/metadata/` for implementation.
```

---

#### 6. CLI breaking changes: download-remote-session

**Location:** `docs/learned/cli/exec-commands.md` + `.claude/skills/erk-exec/reference.md`
**Action:** UPDATE
**Source:** [PR #7757]

**Draft Content:**

```markdown
## download-remote-session

Downloads a session from a remote branch.

### Breaking Change (PR #7757)

Parameter `--gist-url` has been replaced with `--session-branch`.

**Before:** `erk exec download-remote-session --gist-url https://gist.github.com/...`
**After:** `erk exec download-remote-session --session-branch session/7757`

The implementation now uses `git show` to read file contents directly from the remote branch rather than fetching from a gist URL.

See `src/erk/cli/commands/exec/scripts/download_remote_session.py` for implementation.
```

---

### MEDIUM Priority

#### 7. Subprocess LBYL canonical examples

**Location:** `docs/learned/architecture/subprocess-wrappers.md` (new section: "False Positive Examples")
**Action:** UPDATE
**Source:** [PR #7757] PR comments (3 false positives from dignified-python-review bot)

**Draft Content:**

```markdown
## LBYL False Positive Examples

The dignified-python-review bot may flag subprocess patterns that are actually correct. Here are canonical examples of valid LBYL usage:

### 1. check=False with explicit returncode check (graceful degradation)

When a subprocess failure should degrade gracefully rather than raise an exception, using `check=False` with explicit returncode checking IS correct LBYL.

See `download_remote_session.py:78` - function returns `None` on failure rather than raising.

### 2. Function contract with `| None` return type

When the function signature promises `str | None`, returning `None` on subprocess failure is the explicit contract, not hidden control flow.

### 3. Fire-and-forget cleanup operations

Cleanup operations that should not block the main workflow can use `check=False` legitimately.

See `trigger_async_learn.py:259` and `trigger_async_learn.py:645` for examples.
```

---

#### 8. Git stash pattern for branch-switching operations

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl] Part 7

**Draft Content:**

```markdown
## Git Stash Pattern for Branch Operations

**Trigger:** Before `upload-session` or operations that switch branches

**Warning:** If git complains about uncommitted changes blocking checkout, use:
```bash
git stash && <command> && git stash pop
```

**Context:** Operations like `upload-session` create/checkout temporary branches. Uncommitted changes block checkout with "local changes would be overwritten" error. The stash pattern temporarily cleans the working directory.

**Tripwire score:** 4 (Non-obvious +2, External tool quirk +1, Repeated pattern +1)
```

---

#### 9. Stash side effects on code execution

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl] Part 7

**Draft Content:**

```markdown
## Git Stash Side Effects

**Trigger:** After using git stash during implementation

**Warning:** Stashed changes revert code to the last committed state. Old implementations may execute temporarily.

**Context:** In PR #7757, stashing uncommitted changes during `upload-session` caused the old gist-based implementation to execute momentarily (since the new branch-based code was in the stash). This was benign but could cause confusion.

**Prevention:** Remember that stashed state is not active code. Verify which version is running if unexpected behavior occurs.

**Tripwire score:** 4 (Non-obvious +2, Silent failure +2)
```

---

#### 10. Prettier version consistency

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl] Part 7

**Draft Content:**

```markdown
## Prettier Version Consistency

**Trigger:** Before running `make fast-ci` or CI formatting checks

**Warning:** If you've modified markdown files, ensure you run prettier using the SAME command that CI uses (global `prettier` vs `npx prettier`). Version/config discrepancies cause confusing CI failures.

**Context:** The Makefile uses global `prettier` command. Devrun agents were using `npx prettier`. These can have different versions or configurations, causing local checks to pass while CI fails.

**Resolution:** Run `prettier --write '**/*.md'` (global command) to match Makefile's prettier-check target.

**Tripwire score:** 4 (Non-obvious +2, Silent failure +2)
```

---

#### 11. Git pull --rebase after impl-context cleanup

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl] Part 1

**Draft Content:**

```markdown
## Post-Cleanup Rebase

**Trigger:** After `.erk/impl-context/` cleanup commit

**Warning:** Run `git pull --rebase origin $(git branch --show-current)` before pushing to avoid non-fast-forward rejection.

**Context:** The impl-context cleanup step creates a commit. If the remote branch has moved (e.g., CI pushed something), the subsequent push will fail with non-fast-forward error.

**Pattern:**
```bash
# After cleanup commit
git pull --rebase origin $(git branch --show-current)
git push
```

**Tripwire score:** 4 (Non-obvious +2, Cross-cutting +2)
```

---

#### 12. macOS sed syntax requirement

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl] Part 5

**Draft Content:**

```markdown
## macOS sed Syntax

**Trigger:** When using sed in bash scripts

**Warning:** Always use `sed -i ''` (empty string) for macOS compatibility, not `sed -i`.

**Context:** macOS requires an explicit backup extension argument for in-place editing. Using Linux syntax (`sed -i`) produces "bad flag in substitute command: 'e'" error.

**Correct pattern:**
```bash
sed -i '' 's/old/new/g' file.txt
```

**Tripwire score:** 4 (Non-obvious +2, Cross-cutting +2)
```

---

#### 13. Testing subprocess-wrapped git operations

**Location:** `docs/learned/testing/test-boundaries.md` (new file or section in testing.md)
**Action:** CREATE
**Source:** [Impl] Parts 5-6

**Draft Content:**

```markdown
# Testing Subprocess-Wrapped Git Operations

## The Boundary Problem

Some exec scripts combine gateway abstractions with direct subprocess calls. This creates a testing boundary:

- **FakeGit**: Records gateway calls (`fetch_branch`, `push_to_remote`) but doesn't create real refs
- **subprocess.run**: Requires real git repo with actual branch/file content

## Example: download_remote_session

The `_download_from_branch` function uses:
1. `git.remote.fetch_branch()` - Testable with FakeGit
2. `subprocess.run(["git", "show", f"origin/{branch}:path"])` - Requires real repo

## Test Strategy

- **Unit tests**: Verify error paths, helpers, CLI validation using FakeGit
- **Integration tests**: Verify success paths with real git repos

See `tests/unit/commands/exec/test_download_remote_session.py` for boundary example.
```

---

#### 14. Gateway sub-gateway discovery pattern

**Location:** `docs/learned/architecture/gateway-abc.md`
**Action:** UPDATE
**Source:** [Impl] Part 2

**Draft Content:**

```markdown
## Sub-Gateway Architecture

Git gateway operations are organized via sub-gateways. The main `GitGateway` ABC provides accessor properties, not operations.

### Available Sub-Gateways

| Property | ABC File | Key Operations |
|----------|----------|----------------|
| `git.remote()` | `remote_ops/abc.py` | `fetch_branch`, `push_to_remote` |
| `git.branch()` | `branch_ops/abc.py` | `create_branch`, `checkout_branch`, `delete_branch` |
| `git.commit()` | `commit_ops/abc.py` | `stage_files`, `commit`, `add_all` |
| `git.status()` | `status_ops/abc.py` | `get_current_branch`, `is_clean` |
| `git.rebase()` | `rebase_ops/abc.py` | `rebase_onto`, `abort_rebase` |

### Discovery Pattern

When looking for git operations, explore sub-gateway ABC files rather than the main `git/abc.py`.

See `packages/erk-shared/src/erk_shared/gateway/git/` for implementation.
```

---

#### 15. Session discovery command output changes

**Location:** `docs/learned/sessions/discovery-fallback.md`
**Action:** UPDATE
**Source:** [PR #7757]

**Draft Content:**

```markdown
## Fallback Hierarchy Update (PR #7757)

Priority 3 changed from "Remote session (gist)" to "Remote session (branch)".

### Updated Output Schema

```json
{
  "last_session_branch": "session/7757",
  ...
}
```

The `last_session_gist_url` field no longer exists.

See `src/erk/cli/commands/exec/scripts/get_learn_sessions.py` for implementation.
```

---

#### 16. Learn workflow session branch cleanup

**Location:** `docs/learned/planning/learn-workflow.md`
**Action:** UPDATE
**Source:** [PR #7757]

**Draft Content:**

```markdown
## Session Branch Cleanup

The learn pipeline now cleans up session branches after extracting materials to the learn branch.

### Cleanup Timing

1. Learn pipeline reads session from `session/{plan_id}` branch
2. Materials extracted to `learn/{plan_id}` branch
3. Session branch deleted via `git.branch.delete_branch()`

### Why Cleanup Matters

Without cleanup, session branches would accumulate. Each re-implementation force-pushes to the same branch, but old branches from completed plans would remain.

See `src/erk/cli/commands/exec/scripts/trigger_async_learn.py` (grep: `cleanup_session_branch`).
```

---

#### 17. Discriminated union field migration pattern

**Location:** `docs/learned/refactoring/field-migration.md`
**Action:** CREATE
**Source:** [Impl] Part 6

**Draft Content:**

```markdown
# Discriminated Union Field Migration

When renaming fields in discriminated unions (dataclasses with type discriminators), follow this systematic approach.

## Steps

1. **Production code**: Rename field in dataclass definition
2. **Schema constants**: Update schema validators (if applicable)
3. **Test helpers**: Update factory functions that construct test objects
4. **Test fixtures**: Update hardcoded field names in test data
5. **Serialization**: Update any JSON/YAML field mappings
6. **Assertions**: Update test assertions checking field values

## Bulk Rename Pattern

For consistent field renames across many files, use sed:

```bash
sed -i '' 's/old_field_name/new_field_name/g' tests/unit/**/*.py
```

## Example

PR #7757 renamed `last_session_gist_url` to `last_session_branch`:
- Updated `SessionsForPlan` dataclass
- Updated `_make_plan_issue_body_with_remote_session` test helper
- Used sed to bulk-rename in test_discovery.py and test_trigger_async_learn.py

See test files in `tests/unit/sessions/` and `tests/unit/commands/exec/` for examples.
```

---

### LOW Priority

#### 18. Draft-PR plan location patterns

**Location:** `docs/learned/planning/draft-pr-patterns.md`
**Action:** UPDATE
**Source:** [Impl] Part 1

**Draft Content:**

```markdown
## Plan File Locations in Draft-PR Workflow

### Disambiguation

| File | Purpose | When to Read |
|------|---------|--------------|
| `.impl/plan.md` | PR description / commit message | When creating PR |
| `.worker-impl/plan.md` | Implementation phases | When implementing |

### Pattern

When `impl_type == "impl"` and plan comes from a draft-PR:
- Read `.worker-impl/plan.md` for implementation phases
- `.impl/plan.md` serves as the PR/commit message, not the implementation guide
```

---

#### 19. Mixed subprocess/gateway pattern

**Location:** `docs/learned/architecture/subprocess-wrappers.md`
**Action:** CREATE (new subsection)
**Source:** [Impl] Part 5

**Draft Content:**

```markdown
## When to Use Direct subprocess.run

Some operations don't have gateway abstractions. Direct subprocess.run is acceptable for:

### git show (file content from refs)

No gateway abstraction exists for retrieving file contents from arbitrary refs. Use:

```python
result = subprocess.run(
    ["git", "show", f"origin/{branch}:{path}"],
    capture_output=True,
    text=True,
    check=False,
)
```

See `_download_from_branch` in `download_remote_session.py` for implementation.

### Testing Implications

Operations using direct subprocess require integration tests with real git repos. FakeGit cannot simulate ref-based file retrieval.
```

---

#### 20. FakeGit mutation tracking API

**Location:** `docs/learned/testing/fake-driven-testing.md`
**Action:** UPDATE
**Source:** [Impl] Part 5

**Draft Content:**

```markdown
## FakeGit Mutation Tracking

FakeGit exposes read-only properties for asserting operation sequences:

| Property | Type | What It Tracks |
|----------|------|----------------|
| `checked_out_branches` | `list[str]` | Branches passed to `checkout_branch()` |
| `created_branches` | `list[str]` | Branches passed to `create_branch()` |
| `pushed_branches` | `list[tuple]` | Branches pushed via `push_to_remote()` |
| `commits` | `list[str]` | Commit messages |
| `staged_files` | `list[Path]` | Files passed to `stage_files()` |

### Assertion Pattern

```python
assert "session/7757" in git.checked_out_branches
assert ("session/7757", True) in git.pushed_branches  # (branch, force)
```

See `packages/erk-shared/src/erk_shared/gateway/git/fake.py` for implementation.
```

---

#### 21. Test migration checklist for gateway changes

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Impl] Part 5

**Draft Content:**

```markdown
## Test Migration Checklist for Gateway Changes

When replacing a gateway dependency (e.g., GitHub to Git), update tests systematically:

- [ ] **Imports**: Replace `FakeGitHub` with `FakeGit` (or appropriate fake)
- [ ] **Context injection**: Update `with_*` context managers in test helpers
- [ ] **Mutation assertions**: Change assertions from old fake's tracking (e.g., `created_gists`) to new fake's tracking (e.g., `pushed_branches`)
- [ ] **Error simulation**: Update error injection parameters (e.g., `gist_create_error` to `push_error`)
- [ ] **Test structure**: Consider if tests should move from unit to integration (see subprocess boundary)

See `tests/unit/commands/exec/test_upload_session.py` for rewrite example.
```

---

#### 22. Gateway ABC removal pattern

**Location:** `docs/learned/architecture/gateway-abc-implementation.md`
**Action:** UPDATE
**Source:** [Impl] Part 4

**Draft Content:**

```markdown
## Gateway Method Removal Checklist

When removing an abstract method from a gateway ABC, update 5+ places:

1. **ABC file**: Remove abstract method and associated types
2. **Real implementation**: Remove method
3. **Fake implementation**: Remove method, tracking state, error simulation params
4. **DryRun implementation**: Remove method
5. **Printing implementation**: Remove method
6. **Imports**: Clean up imports in all affected files

### Example: create_gist removal (PR #7757)

- Removed `create_gist` abstract method from `github/abc.py`
- Removed `GistCreated` and `GistCreateError` types from `abc.py`
- Removed implementation from `real.py`
- Removed fake implementation + `_created_gists`, `_next_gist_id`, `gist_create_error` from `fake.py`
- Removed stub from `dry_run.py`
- Removed logging wrapper from `printing.py`
```

---

#### 23. Branch lifecycle automation pattern

**Location:** `docs/learned/architecture/branch-automation.md`
**Action:** CREATE or UPDATE
**Source:** [Impl] Part 2

**Draft Content:**

```markdown
# Branch Lifecycle Automation Pattern

For operations that create temporary branches, follow this pattern:

```python
original_branch = git.status.get_current_branch()
try:
    # Delete existing local branch if present
    git.branch.delete_branch(target_branch, force=True)
    # Create from remote ref
    git.branch.create_branch(target_branch, f"origin/{base_branch}")
    git.branch.checkout_branch(target_branch)
    # ... do work ...
finally:
    git.branch.checkout_branch(original_branch)
```

### Key Elements

1. **Save original branch**: Restore at end
2. **Delete existing local**: Ensures clean state
3. **Create from remote**: Uses `origin/master` or appropriate base
4. **Finally block**: Guarantees branch restoration on failure

See `trigger_async_learn.py` for reference implementation.
```

---

#### 24. Best-effort GitHub signal failures

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Parts 1, 7

**Draft Content:**

```markdown
## Best-Effort impl-signal Failures

**Trigger:** When impl-signal commands fail with "plan-header block not found"

**Context:** The `impl-signal` command is best-effort. Failures are expected for draft PRs that don't have plan-header metadata blocks.

**Resolution:** Suppress with `|| true` in CI scripts when the operation is non-critical.

**Tripwire score:** 2 (Non-obvious +2, but expected behavior)
```

---

#### 25. SessionSource property rename

**Location:** `docs/learned/planning/session-source.md`
**Action:** UPDATE
**Source:** [PR #7757]

**Draft Content:**

```markdown
## SessionSource Property Change (PR #7757)

The `gist_url` property has been renamed to `session_branch` on the `SessionSource` ABC.

### Updated Interface

```python
class SessionSource(ABC):
    @property
    @abstractmethod
    def session_branch(self) -> str | None:
        """Branch name where session is stored, or None for local sessions."""
```

### RemoteSessionSource

Constructor parameter changed from `gist_url` to `session_branch`.

See `packages/erk-shared/src/erk_shared/learn/extraction/session_source.py` for implementation.
```

---

#### 26. upload-session command behavior changes

**Location:** `docs/learned/cli/exec-commands.md`
**Action:** UPDATE
**Source:** [PR #7757]

**Draft Content:**

```markdown
## upload-session

Uploads a session JSONL file to a git branch.

### Behavior Change (PR #7757)

Previously created a GitHub gist. Now commits to `session/{plan_id}` branch.

### New Workflow

1. Saves current branch
2. Deletes local `session/{plan_id}` if exists
3. Creates branch from `origin/master`
4. Copies session file to `.erk/session/session-{session_id}.jsonl`
5. Commits and force-pushes
6. Updates plan-header metadata with `last_session_branch`
7. Restores original branch

### Output

```json
{
  "session_branch": "session/7757"
}
```

See `src/erk/cli/commands/exec/scripts/upload_session.py` for implementation.
```

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Prettier Version Inconsistency

**What happened:** CI failed on prettier check despite local prettier --write appearing to succeed.
**Root cause:** Makefile uses global `prettier` command while devrun agent was using `npx prettier`. Different executables can have different versions/configurations.
**Prevention:** Always use the exact same prettier command pattern that CI uses when running local checks.
**Recommendation:** TRIPWIRE

### 2. Git Stash Reverting to Old Code

**What happened:** During `upload-session`, stashing uncommitted changes caused the old gist-based implementation to execute momentarily.
**Root cause:** Stashing removes uncommitted changes from the working directory, reverting to the last committed state.
**Prevention:** Remember that stashed changes are not active code. Verify which version is running if unexpected behavior occurs.
**Recommendation:** TRIPWIRE

### 3. Non-Fast-Forward Push After Cleanup

**What happened:** `git push` failed after impl-context cleanup commit.
**Root cause:** Remote branch had moved ahead while local changes were being made.
**Prevention:** Run `git pull --rebase` before any local commits during setup.
**Recommendation:** TRIPWIRE

### 4. macOS sed Syntax Error

**What happened:** sed command failed with "bad flag in substitute command: 'e'".
**Root cause:** Linux sed syntax (`sed -i`) doesn't work on macOS, which requires `sed -i ''`.
**Prevention:** Always use `sed -i ''` (empty string) for macOS compatibility.
**Recommendation:** TRIPWIRE

### 5. Unit Tests Failing with Subprocess

**What happened:** Changed implementation from FakeGit-able operations to subprocess-based `git show`, causing unit tests to fail.
**Root cause:** FakeGit records `fetch_branch()` calls but doesn't create refs, so subsequent `git show` subprocess fails.
**Prevention:** Before adding subprocess.run, verify FakeGit support or plan integration test strategy.
**Recommendation:** ADD_TO_DOC (testing boundaries doc)

### 6. Schema Validation Order Violation (Avoided)

**What happened:** Agent correctly identified risk and avoided it.
**Root cause:** Updating callers before schema would cause validation errors.
**Prevention:** Always trace validation flow before editing. If code calls schema-validated APIs, update schema FIRST.
**Recommendation:** ADD_TO_DOC (schema migrations doc)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Git stash before branch-switching operations

**Score:** 4/10 (Non-obvious +2, External tool quirk +1, Repeated pattern +1)
**Trigger:** Before `upload-session` or operations that switch branches
**Warning:** If git reports uncommitted changes blocking checkout, use `git stash && <command> && git stash pop` to temporarily clean working directory.
**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because the error message ("local changes would be overwritten") doesn't suggest the stash solution. Agents encountering this for the first time will spend cycles debugging rather than applying the standard workaround.

### 2. Stash side effects on code execution

**Score:** 4/10 (Non-obvious +2, Silent failure +2)
**Trigger:** After using git stash during implementation
**Warning:** Stashed changes revert code to last committed state; old implementations may execute temporarily.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because the side effect is silent and non-obvious. An agent may stash, run a command, and be confused why the "new" implementation isn't working - not realizing the stash reverted to old code.

### 3. Prettier version consistency (npx vs global)

**Score:** 4/10 (Non-obvious +2, Silent failure +2)
**Trigger:** Before running CI checks
**Warning:** Ensure prettier command matches CI (global vs npx); version/config mismatches cause failures.
**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy because the failure is confusing - local checks pass, CI fails. The root cause (different executables) is not obvious from the error message.

### 4. Git pull --rebase after impl-context cleanup

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** After `.erk/impl-context/` cleanup commit
**Warning:** Run `git pull --rebase` before push to avoid non-fast-forward rejection.
**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because the cleanup step is part of a standard workflow, and the push failure disrupts the flow. Agents should preemptively rebase rather than react to the error.

### 5. macOS sed syntax with -i flag

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** Before using sed in bash scripts
**Warning:** Use `sed -i ''` (empty string) for macOS compatibility, not `sed -i`.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because it's a platform-specific gotcha that affects any sed usage. The error message is cryptic and doesn't suggest the fix.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Gateway sub-gateway discovery

**Score:** 3/10 (Non-obvious +2, Cross-cutting +1)
**Notes:** Pattern is discoverable but not immediately obvious. Agent spent time exploring multiple abc.py files. May warrant tripwire if multiple agents hit this.

### 2. Schema-first migration order

**Score:** 3/10 (Non-obvious +2, Cross-cutting +1)
**Notes:** Critical ordering but contained to schema migrations. Documented in schema-migrations.md is sufficient unless errors recur.

### 3. Unit vs integration boundary for subprocess

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Not destructive, but confusing when tests fail. Documented in testing boundaries doc.

### 4. Session branch force-push discipline

**Score:** 3/10 (Cross-cutting +2, Destructive potential +1)
**Notes:** Only CI should force-push session branches. Low risk since branches are ephemeral and cleaned up.

### 5. Field rename in discriminated unions

**Score:** 3/10 (Non-obvious +1, Repeated pattern +1, Cross-cutting +1)
**Notes:** Systematic but straightforward with grep. Document in refactoring guide.

### 6. Draft-PR plan file location

**Score:** 3/10 (Non-obvious +2, Cross-cutting +1)
**Notes:** Specific to draft-PR workflow, not all plans. Documented in draft-pr-patterns.md.

### 7. Best-effort impl-signal failures

**Score:** 2/10 (Non-obvious +2)
**Notes:** Expected behavior for draft PRs. Context-only documentation.

### 8. FakeGit mutation tracking properties

**Score:** 2/10 (Non-obvious +1, Cross-cutting +1)
**Notes:** Standard fake pattern, just needs documentation reference.
