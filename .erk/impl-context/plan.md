# Documentation Plan: Eliminate .worker-impl/ — consolidate on .erk/impl-context/

## Context

PR #7901 eliminates the `.worker-impl/` staging directory and consolidates on `.erk/impl-context/` as the sole git-committed staging directory for plan content during remote implementation workflows. This architectural simplification removes conceptual complexity by having one directory for committed plan transport instead of two confusingly-named directories (`.worker-impl/` with `plan-ref.json` versus `.erk/impl-context/` with `ref.json`).

The implementation demonstrates several important patterns that future agents will benefit from understanding: time abstraction via `now_iso` parameter injection for testability, LBYL-style JSON parsing with helper extraction (`_parse_ref_json`), and graceful fallback chains for metadata format evolution. Additionally, the sessions implementing this change revealed valuable operational patterns around branch name recovery, objective update workflows, and plan-save idempotency.

Documentation of this work serves dual purposes: (1) capturing the architectural decisions and APIs for developers working with the impl-context system, and (2) recording the prevention insights and tripwires discovered during implementation to help future agents avoid repeating mistakes.

## Raw Materials

See attached session analyses and diff analysis in `.erk/scratch/sessions/fae950ab-a47c-419a-a94b-8c3794da1db5/learn-agents/`

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 16    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 4     |

## Documentation Items

### HIGH Priority

#### 1. Document ref.json fallback chain

**Location:** `docs/learned/architecture/ref-json-migration.md`
**Action:** CREATE
**Source:** [PR #7901], [Impl]

**Draft Content:**

```markdown
---
read-when:
  - working with plan reference metadata
  - implementing fallback logic for metadata files
  - migrating between reference file formats
tripwires: 2
---

# Reference JSON Migration and Fallback Chain

## Summary

Plan reference metadata evolved through three formats. The `read_plan_ref()` function implements a graceful fallback chain to support all formats.

## Format Evolution

1. **issue.json (legacy)** - Original format, no longer created
2. **plan-ref.json (.impl/)** - User-facing implementation folder, written by `save_plan_ref()`
3. **ref.json (.erk/impl-context/)** - Staging folder for remote workflows, written by `create_impl_context()`

## Fallback Chain

The `read_plan_ref()` function tries formats in order:
1. `plan-ref.json` (primary for .impl/)
2. `ref.json` (primary for .erk/impl-context/)
3. Returns None if neither exists

See `packages/erk-shared/src/erk_shared/impl_folder.py`, grep for "def read_plan_ref"

## Schema Validation

Both formats share the same required fields, validated via `_REQUIRED_REF_FIELDS` constant:
- `plan_id`
- `plan_url`
- `created_at`
- `provider` (optional, defaults to "github")

See `packages/erk-shared/src/erk_shared/impl_folder.py`, grep for "_REQUIRED_REF_FIELDS"

## When to Use Each

| Format | Directory | Written By | Purpose |
|--------|-----------|------------|---------|
| plan-ref.json | .impl/ | `save_plan_ref()` | User-facing implementation folder |
| ref.json | .erk/impl-context/ | `create_impl_context()` | CI staging, plan transport via git |

## Tripwires

- ALWAYS check both plan-ref.json and ref.json when reading plan references
- NEVER write ref.json directly in .impl/ - use save_plan_ref() for consistency
```

---

#### 2. Update issue-reference-flow.md with fallback logic

**Location:** `docs/learned/architecture/issue-reference-flow.md`
**Action:** UPDATE
**Source:** [PR #7901]

**Draft Content:**

```markdown
## Updates Needed

Add section documenting:

1. `read_plan_ref()` now implements two-step fallback: plan-ref.json -> ref.json
2. Distinction between save_plan_ref() (writes plan-ref.json for .impl/) and create_impl_context() (writes ref.json directly for .erk/impl-context/)
3. Code pointer: packages/erk-shared/src/erk_shared/impl_folder.py, grep for "def read_plan_ref"

## Key Points

- read_plan_ref() reads either format transparently
- save_plan_ref() only writes plan-ref.json (for .impl/ folder)
- create_impl_context() writes ref.json directly (for .erk/impl-context/)
- Both use _REQUIRED_REF_FIELDS for schema validation
```

---

#### 3. Document impl_context.py three-function API

**Location:** `docs/learned/architecture/impl-context-api.md`
**Action:** CREATE
**Source:** [PR #7901], [Impl]

**Draft Content:**

```markdown
---
read-when:
  - creating or managing .erk/impl-context/ folders
  - working with remote implementation workflows
  - setting up plan transport via git
tripwires: 3
---

# Impl-Context API

## Summary

The impl_context module provides a three-function API for managing `.erk/impl-context/` folders - the staging directory for plan content during remote implementation workflows.

## Functions

### create_impl_context()

Creates the `.erk/impl-context/` folder with plan.md and ref.json.

Parameters:
- `plan_content: str` - Markdown content of the plan
- `plan_id: int` - GitHub issue number
- `url: str` - URL to the plan issue
- `repo_root: Path` - Repository root
- `provider: str` - Plan backend provider (default: "github")
- `objective_id: int | None` - Optional parent objective
- `now_iso: str` - ISO timestamp (for testability)

See `packages/erk-shared/src/erk_shared/impl_context.py`, grep for "def create_impl_context"

### remove_impl_context()

Removes the `.erk/impl-context/` folder and all contents.

### impl_context_exists()

Checks if `.erk/impl-context/` folder exists.

## Folder Structure

```
.erk/impl-context/
  plan.md      # Plan content
  ref.json     # Metadata (plan_id, url, created_at, provider, objective_id)
```

Note: NO README.md - this is a staging directory, not user-facing.

## Difference from .impl/

| Aspect | .impl/ | .erk/impl-context/ |
|--------|--------|-------------------|
| Visibility | User-facing | Automation-only |
| Git status | Ephemeral (not committed) | Committed for transport |
| Contents | plan.md, plan-ref.json, README.md | plan.md, ref.json |
| Written by | save_plan_ref() | create_impl_context() |

## Time Abstraction

The `now_iso` parameter enables testability. Callers inject timestamps:
- Production: `ctx.time.now().isoformat()`
- Tests: `"2025-01-15T10:30:00+00:00"`

## Tripwires

- NEVER use .worker-impl/ - it was deleted in PR #7901
- ALWAYS inject now_iso parameter - never call datetime.now() directly
- README.md is intentionally omitted from .erk/impl-context/
```

---

#### 4. Batch update 6 docs referencing .worker-impl/

**Location:** Multiple files (batch update)
**Action:** UPDATE
**Source:** [PR #7901]

**Draft Content:**

Update these 6 files to remove .worker-impl/ references and reflect single-directory architecture:

1. **docs/learned/planning/worktree-cleanup.md**
   - Remove .worker-impl/ ownership section
   - Update cleanup patterns to reference only .erk/impl-context/

2. **docs/learned/architecture/impl-folder-lifecycle.md**
   - Remove .worker-impl/ table entry
   - Consolidate lifecycle description on .erk/impl-context/

3. **docs/learned/planning/impl-context.md**
   - Expand to cover both staging AND implementation directory roles
   - Clarify .erk/impl-context/ is sole staging directory

4. **docs/learned/planning/lifecycle.md**
   - Update Phase 4/5 to reference .erk/impl-context/ instead of .worker-impl/

5. **docs/learned/planning/workflow.md**
   - Update folder structure examples to remove .worker-impl/

6. **docs/learned/planning/tripwires.md**
   - Update tripwires referencing .worker-impl/ to reference .erk/impl-context/
   - Add "NEVER create .worker-impl/ folders" tripwire

---

### MEDIUM Priority

#### 5. Update exec-commands.md with renamed command

**Location:** `docs/learned/cli/exec-commands.md`
**Action:** UPDATE
**Source:** [PR #7901]

**Draft Content:**

```markdown
## create-impl-context-from-plan

Creates .erk/impl-context/ folder from a plan issue.

**Usage:** `erk exec create-impl-context-from-plan <plan-id>`

**Output (JSON):**
- `success: bool`
- `impl_context_path: str`
- `plan_id: int`
- `plan_url: str`

**Exit codes:**
- 0: Success
- 1: plan_not_found

**Breaking change:** Renamed from `create-worker-impl-from-issue` in PR #7901. No backward compatibility.

See `src/erk/cli/commands/exec/scripts/create_impl_context_from_plan.py`
```

---

#### 6. Verify composite-action-patterns.md completeness

**Location:** `docs/learned/ci/composite-action-patterns.md`
**Action:** UPDATE
**Source:** [PR #7901]

**Draft Content:**

Verify the check-impl-context section includes:

- Purpose: CI skip detection when .erk/impl-context/ exists
- Output: `skip=true/false`
- Usage pattern: Conditional job execution via `if: steps.check.outputs.skip != 'true'`
- Migration note: Renamed from check-worker-impl (just naming change)
- Code pointer: `.github/actions/check-impl-context/action.yml`

---

#### 7. Verify plan-implement-workflow-patterns.md completeness

**Location:** `docs/learned/ci/plan-implement-workflow-patterns.md`
**Action:** UPDATE
**Source:** [PR #7901]

**Draft Content:**

Verify workflow documentation includes:

- Exec command: `create-impl-context-from-plan` (not `create-worker-impl-from-issue`)
- Cleanup: Single `.erk/impl-context/` block (not two blocks for .worker-impl and .erk/impl-context)
- Copy step: `cp -r .erk/impl-context .impl`
- Git filter: Exclude `.erk/impl-context/` from uncommitted changes check
- Code pointer: `.github/workflows/plan-implement.yml`

---

#### 8. Document JSON parsing DRY pattern

**Location:** `docs/learned/architecture/json-parsing-patterns.md`
**Action:** CREATE
**Source:** [PR #7901]

**Draft Content:**

```markdown
---
read-when:
  - parsing JSON configuration files
  - validating JSON schemas in Python
  - implementing fallback logic for multiple file formats
tripwires: 1
---

# JSON Parsing Patterns

## Summary

When parsing JSON files with required fields, extract constants and helper functions to avoid duplication.

## Pattern: Constants + Helper

```python
# Define required fields as module constant
_REQUIRED_REF_FIELDS = ("plan_id", "plan_url", "created_at")

def _parse_ref_json(path: Path) -> PlanRef | None:
    """Parse and validate ref.json file."""
    if not path.exists():
        return None

    data = json.loads(path.read_text())

    # LBYL: Check all required fields present
    if not all(field in data for field in _REQUIRED_REF_FIELDS):
        return None

    return PlanRef(
        plan_id=data["plan_id"],
        plan_url=data["plan_url"],
        ...
    )
```

## Benefits

1. **DRY**: Field list defined once, used for validation
2. **LBYL compliant**: Check before access, no try/except
3. **Reusable**: Same helper works for multiple file formats with same schema
4. **Testable**: Constants can be referenced in tests

See `packages/erk-shared/src/erk_shared/impl_folder.py`, grep for "_parse_ref_json"

## Tripwires

- NEVER copy-paste field validation logic across parsers
- ALWAYS extract _REQUIRED_FIELDS constant when validating JSON schemas
```

---

#### 9. Update erk-architecture.md with time abstraction example

**Location:** `docs/learned/architecture/erk-architecture.md`
**Action:** UPDATE
**Source:** [PR #7901]

**Draft Content:**

Add concrete example under Time Abstraction section:

```markdown
## Time Abstraction Example

The `create_impl_context()` function demonstrates proper time abstraction:

```python
def create_impl_context(
    *,
    plan_content: str,
    plan_id: int,
    now_iso: str,  # Injected, not computed
    ...
) -> Path:
    ref_data = {
        "created_at": now_iso,  # Use injected value
        ...
    }
```

Callers inject timestamps from the context system:

```python
# Production
create_impl_context(now_iso=ctx.time.now().isoformat(), ...)

# Tests
create_impl_context(now_iso="2025-01-15T10:30:00+00:00", ...)
```

See `packages/erk-shared/src/erk_shared/impl_context.py`, grep for "now_iso"
```

---

#### 10. Document no README.md decision

**Location:** `docs/learned/planning/impl-context.md`
**Action:** UPDATE
**Source:** [PR #7901]

**Draft Content:**

Add section clarifying the intentional omission:

```markdown
## No README.md in .erk/impl-context/

The `.erk/impl-context/` directory intentionally omits README.md:

| Directory | README.md | Rationale |
|-----------|-----------|-----------|
| .impl/ | Yes | User-facing, needs explanation |
| .erk/impl-context/ | No | Automation-only staging, not documentation |

The folder contains only:
- `plan.md` - Plan content
- `ref.json` - Metadata for plan identification

This design decision was made in PR #7901 to keep the staging directory minimal.
```

---

#### 11. Add branch name recovery tripwire

**Location:** `docs/learned/planning/tripwires.md` or `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Session 8e19182b]

**Draft Content:**

Add tripwire:

```markdown
## Branch Name Truncation

**Trigger:** Before using branch name from UI or screenshot

**Warning:** Use `gh pr view <pr-number> --json headRefName` to retrieve full branch name instead of trusting UI displays.

**Context:** UI elements often truncate long branch names. For example, `plnd/O7823-plan-improve-code-le-02-22-2315` may appear as `plnd/07823-plan-im`. Commands will fail with incorrect branch names.

**Solution:**
```bash
gh pr view 7919 --json headRefName --jq .headRefName
```

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
```

---

#### 12. Add objective branch naming convention

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE
**Source:** [Session 8e19182b]

**Draft Content:**

Add to naming conventions:

```markdown
## Objective Branch Naming

Objective branches use capital letter **O** (not digit 0):

| Correct | Incorrect |
|---------|-----------|
| `plnd/O7823-...` | `plnd/07823-...` |

The capital O distinguishes objective-related branches from other numbered references.

Example: Objective #7823 creates branch `plnd/O7823-plan-improve-...`
```

---

### LOW Priority

#### 13. Document plan-save idempotency

**Location:** `docs/learned/planning/workflow.md` or `docs/learned/planning/lifecycle.md`
**Action:** UPDATE
**Source:** [Session 5b5f19e0-part2], [Session 930cc591]

**Draft Content:**

```markdown
## Plan-Save Idempotency

The `plan-save` command uses session-scoped marker files to prevent duplicates:

- Marker location: `.erk/markers/plan-saved-issue`
- Detection: Command checks marker before GitHub API call
- Response for duplicate: `{"success": true, "skipped_duplicate": true, "message": "Session already saved plan #NNNN"}`

This pattern:
- Prevents duplicate plan issues within same session
- Allows saves across different sessions
- Uses lightweight marker files instead of database

When handling `skipped_duplicate`, agents should fetch PR details and display same output as if plan had just been saved.
```

---

#### 14. Document exit-plan-mode hook flow

**Location:** `docs/learned/hooks/`
**Action:** CREATE or UPDATE
**Source:** [Session 5b5f19e0-part2]

**Draft Content:**

```markdown
## Exit-Plan-Mode Hook

The `PreToolUse:ExitPlanMode` hook intercepts plan mode exit to present options.

### Three-Option Flow

1. **"Create a plan PR"** - Delegates to `/erk:plan-save` skill
2. **"Skip PR and implement here"** - Proceeds with local implementation
3. **"View/Edit the plan"** - Returns to editing

### Trunk Detection

Hook reorders recommendations based on location:
- On trunk (master): "new slot" recommended first
- In a slot: "same slot" recommended first

### Skill Delegation

The hook delegates to skills for complex operations rather than embedding logic:
- `/erk:plan-save` handles PR creation
- This separation allows skills to be tested and maintained independently

### Pattern

Hooks act as routers (decision points), not executors (implementation). They display choices and delegate to skills.
```

---

#### 15. Document matched_steps fallback

**Location:** `docs/learned/objectives/` or `docs/learned/planning/objective-update-patterns.md`
**Action:** CREATE
**Source:** [Session 8e19182b]

**Draft Content:**

```markdown
## Matched Steps Fallback

When `objective-fetch-context` returns empty `matched_steps`:

### Why It Happens

Plans not explicitly linked to objective nodes during creation don't have automatic step matching.

### Fallback Pattern

1. Fetch objective body: `gh issue view <objective-number> --json body`
2. Fetch plan body: `gh issue view <plan-number> --json body` or `gh pr view <pr-number> --json body`
3. Compare plan scope against roadmap node descriptions
4. Manually identify which nodes the plan addresses

### Example

Plan body mentions "improve code-level documentation for backpressure gates"
Roadmap node 3.3 says "Improve backpressure gate documentation"
-> Node 3.3 is the matched step

### When to Use

During objective update workflows when automated matching fails and `matched_steps` is empty.
```

---

#### 16. Verify exec-script-testing.md covers PlanBackend pattern

**Location:** `docs/learned/testing/exec-script-testing.md`
**Action:** UPDATE
**Source:** [PR #7901]

**Draft Content:**

Verify documentation includes:

```markdown
## Testing with PlanBackend

For exec scripts that fetch plan content:

```python
fake_issues = FakeGitHubIssues(
    issues=[IssueInfo(number=123, title="Plan Title", body="Plan content...")]
)
ctx = ErkContext.for_test(github_issues=fake_issues, repo_root=tmp_path)
```

### Assertions

Verify JSON output structure:
- `success: bool`
- `impl_context_path: str`
- `plan_id: int`
- `plan_url: str`

### Error Paths

Test both success and error cases:
- Success: Plan found and impl-context created
- plan_not_found: Exit code 1, error message in JSON

Example: `tests/unit/cli/commands/exec/scripts/test_create_impl_context_from_plan.py`
```

---

## Stale Documentation Cleanup

**Status: No phantom references detected pre-landing**

All code references in existing documentation point to files that exist. However, after PR #7901 lands, 6 documents will reference deleted files and must be updated (covered in HIGH Priority item #4 above).

Post-landing cleanup:
- Remove references to `worker_impl_folder.py` (deleted)
- Remove references to `check-worker-impl` action (deleted)
- Remove references to `.worker-impl/` directory (eliminated)

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Time Abstraction Violation

**What happened:** Initial implementation called `datetime.now(UTC)` directly, caught by automated reviewer.

**Root cause:** Training data suggests `datetime.now()` for timestamps; erk requires injection.

**Prevention:** Document time abstraction prominently. The automated PR review bot caught this before human review - demonstrating the value of bot-enforced tripwires.

**Recommendation:** UPDATE_EXISTING - Add concrete example to erk-architecture.md (covered in item #9)

### 2. Branch Name Truncation

**What happened:** `objective-fetch-context` failed with "No plan found for branch 'plnd/07823-plan-im'" because branch name was truncated in UI.

**Root cause:** UI truncates long branch names in displays and screenshots.

**Prevention:** Always use `gh pr view <pr-number> --json headRefName` to recover full branch name.

**Recommendation:** TRIPWIRE - Add to planning/tripwires.md (covered in item #11)

### 3. objective-fetch-context Fails on Deleted Branches

**What happened:** After landing a PR, the branch is deleted. Subsequent `objective-fetch-context` calls fail because branch doesn't exist.

**Root cause:** Command assumes branch exists to look up plan metadata.

**Prevention:** When branch is deleted, use `gh issue view` and `gh pr view` to manually fetch context.

**Recommendation:** CONTEXT_ONLY - Document as fallback pattern in session analysis

### 4. Documentation Drift Detection

**What happened:** PR review comments identified 8 documentation inaccuracies (stale file paths, outdated folder structure descriptions).

**Root cause:** Docs referenced old file formats (issue.json vs ref.json).

**Prevention:** Use audit-pr-docs bot consistently. The 8 findings demonstrate effective drift detection.

**Recommendation:** CONTEXT_ONLY - Validates existing audit workflow

### 5. Duplicate Field Validation Logic

**What happened:** Initial implementation copy-pasted JSON parsing validation across formats.

**Root cause:** Quick implementation without considering DRY patterns.

**Prevention:** Extract `_REQUIRED_FIELDS` constant and `_parse_helper` function immediately.

**Recommendation:** ADD_TO_DOC - Document pattern in json-parsing-patterns.md (covered in item #8)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Time Abstraction Violation

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)

**Trigger:** Before calling `datetime.now()` in any function

**Warning:** NEVER use `datetime.now()` directly. Always inject `now_iso` parameter and use `ctx.time.now().isoformat()` in caller for testability.

**Target doc:** `docs/learned/architecture/erk-architecture.md` or `docs/learned/universal-tripwires.md`

This is tripwire-worthy because time-based bugs are notoriously difficult to debug in tests, and the pattern applies across all erk code. Automated reviewers catch this, but documenting as a tripwire provides earlier prevention.

### 2. Branch Name Truncation

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)

**Trigger:** Before using branch name from UI or screenshot

**Warning:** Use `gh pr view <pr-number> --json headRefName` to retrieve full branch name instead of trusting UI displays.

**Target doc:** `docs/learned/planning/tripwires.md` or `docs/learned/architecture/tripwires.md`

This affects any workflow that accepts branch names from external sources. Session 8e19182b demonstrated the error pattern and recovery approach.

### 3. Multi-Node Objective Update Race Condition

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)

**Trigger:** Before updating multiple objective nodes

**Warning:** ALWAYS pass all nodes as multiple `--node` flags in a SINGLE command. Sequential calls cause race conditions and duplicate API calls.

**Target doc:** `docs/learned/objectives/tripwires.md`

This prevents subtle bugs where sequential updates cause GitHub API rate limiting or state corruption. Discovered in Session 5b5f19e0-part1.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. objective-fetch-context Fails on Deleted Branches

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)

**Notes:** Medium severity but has manual workaround. If this error recurs frequently, promote to full tripwire with documented fallback pattern (use `gh issue view` + `gh pr view`).

### 2. Empty matched_steps Fallback

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)

**Notes:** Occurred in Session 8e19182b. Pattern is documented as fallback, but if agents repeatedly struggle with this, promote to tripwire.

### 3. Documentation Must Match Code

**Score:** 2/10 (Non-obvious +2)

**Notes:** PR comment #2 emphasized verifying folder structure docs against implementation. The audit-pr-docs bot handles this, but could warrant tripwire if manual verification is needed.

### 4. Prettier Audit After .prettierignore Changes

**Score:** 2/10 (Non-obvious +2)

**Notes:** PR comment #6 noted auditing docs that reference Prettier failures after adding ignored paths. Borderline - may not recur often enough for tripwire status.

---

## Cornerstone Redirects (SHOULD_BE_CODE)

Items that belong in code artifacts rather than learned docs:

### 1. _REQUIRED_REF_FIELDS Constant

**Current state:** Module-level constant in impl_folder.py

**Recommended action:** Add module docstring to `packages/erk-shared/src/erk_shared/impl_folder.py` explaining the validation schema.

**Rationale:** Single-artifact catalog - the required fields are specific to one module's functionality and should be documented in that module's docstring.

### 2. Individual Exec Script Parameters

**Current state:** Parameters undocumented

**Recommended action:** Add docstrings to exec script functions with parameter descriptions.

**Rationale:** Single-artifact API reference - parameter documentation belongs with the code.

### 3. Test Helper Patterns for impl_context

**Current state:** Embedded in test files

**Recommended action:** Keep in test code with good naming; test patterns are self-documenting.

**Rationale:** Test-specific helpers belong in tests, not learned docs.

---

## Documentation Consolidation Opportunities

### Consolidation 1: Reference Metadata Files

**Current state:** Reference metadata documented in 4+ separate locations:
- planning/lifecycle.md
- erk/issue-pr-linkage-storage.md
- architecture/issue-reference-flow.md
- architecture/impl-folder-lifecycle.md

**Recommendation:** Create `docs/learned/architecture/ref-json-migration.md` as single authoritative source (HIGH Priority item #1), then update other docs to link to it.

### Consolidation 2: .worker-impl/ vs .erk/impl-context/

**Current state:** worktree-cleanup.md and impl-folder-lifecycle.md both describe folder ownership with partial overlap.

**Recommendation:** After PR #7901 lands, merge into single authoritative source in `docs/learned/architecture/impl-folder-lifecycle.md`.

---

## Implementation Order

### Phase 1: HIGH Priority (Complete Before Landing PR)

1. Create **ref-json-migration.md** (consolidates metadata file evolution)
2. Update **issue-reference-flow.md** (ref.json fallback)
3. Create **impl-context-api.md** (three-function API)
4. Batch update 6 docs removing .worker-impl/ references

### Phase 2: MEDIUM Priority (Complete Within Sprint)

5. Update **exec-commands.md** (renamed command)
6. Verify **composite-action-patterns.md** completeness
7. Verify **plan-implement-workflow-patterns.md** completeness
8. Create **json-parsing-patterns.md** (DRY pattern)
9. Update **erk-architecture.md** (time abstraction example)
10. Update **impl-context.md** (no README.md decision)
11. Add branch name recovery tripwire
12. Add objective branch naming convention

### Phase 3: LOW Priority (Complete Within Month)

13. Document plan-save idempotency
14. Document exit-plan-mode hook flow
15. Document matched_steps fallback
16. Verify exec-script-testing.md PlanBackend coverage

### Phase 4: Continuous

17. Add 3 high-score tripwires to appropriate docs
18. Monitor potential tripwires for promotion

---

## Success Metrics

Documentation will be considered complete when:

1. All 8 NEW items created (items #1, #3, #8, #14, #15 + tripwire additions)
2. All 8 UPDATE items verified/updated
3. All 3 tripwires (score >= 4) added to appropriate docs
4. No references to deleted files (.worker-impl/, worker_impl_folder.py, check-worker-impl)
5. Consolidation complete for reference metadata files (single authoritative source)
6. All code pointers in new docs use "See file.py, grep for X" pattern

---

## Attribution Summary

| Source | Candidates Contributed | Key Insights |
|--------|------------------------|--------------|
| Code Diff Analyzer | 23 | Complete inventory, design decisions, breaking changes |
| Session 32e93701 | 4 | Objective reevaluation, metadata confusion, GitHub number space |
| Session 5b5f19e0-part1 | 4 | Branch lookup failure, objective update workflow |
| Session 5b5f19e0-part2 | 3 | Plan-save idempotency, exit-plan-mode hook, skill delegation |
| Session 8e19182b | 5 | Branch name truncation, case sensitivity, matched steps fallback |
| Session 930cc591 | 2 | Command palette (different context), plan-save duplicate |
| Session d0ca17bb | 1 | Sparkline visualization (different context) |
| PR Comments | 10 | Documentation drift detection, audit process validation |
