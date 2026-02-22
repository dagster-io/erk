# Documentation Plan: Eliminate checkout from gt track operations

## Context

This PR (#7790) represents a significant architectural simplification in how erk interacts with Graphite's branch tracking commands. The core discovery was that `gt track <branch> --parent <parent>` accepts branch names positionally, meaning it does NOT require the target branch to be checked out first. This eliminated 18 lines of save-current-branch/checkout-target/track/restore-original-branch logic from `GraphiteBranchManager.create_branch()` and `retrack_branch()`.

Beyond the Graphite simplification, PR #7790 includes several breaking changes that require documentation updates: strict ValueError enforcement for unknown metadata schema fields (replacing silent warnings), TUI column consolidation that removes dedicated PR status columns in favor of emoji suffixes, and removal of OAuth token support from the admin CLI. These changes reflect a "fail fast" philosophy for data validation and a cleaner UI presentation.

Documentation matters here because the existing docs explicitly describe the checkout-restore pattern as necessary behavior. Without updates, agents will continue to write unnecessarily complex Graphite integration code. The tripwire-worthy discovery about `gt track` positional syntax should prevent future agents from re-introducing checkout cycles.

## Raw Materials

See PR #7790 for complete implementation details.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 11    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 1     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. gt track positional syntax discovery

**Location:** `docs/learned/architecture/graphite-track-positional.md`
**Action:** CREATE
**Source:** [PR #7790]

**Draft Content:**

```markdown
---
title: "gt track Positional Branch Syntax"
read_when:
  - "calling gt track programmatically"
  - "implementing branch tracking in erk code"
  - "working with GraphiteBranchManager or GraphiteBranchOps"
tripwires:
  - action: "checking out a branch before calling gt track"
    warning: "FORBIDDEN: gt track accepts branch names positionally. Never checkout temporarily to call gt track. Use `gt track <branch> --parent <parent>` directly."
last_audited: "YYYY-MM-DD HH:MM PT"
audit_result: new
---

# gt track Positional Branch Syntax

## Discovery

Graphite's `gt track` command accepts branch names as a positional argument, not just as the current checked-out branch. This means:

- `gt track <branch-name> --parent <parent>` works without checkout
- No need to save current branch, checkout target, track, then restore

## Why This Matters

Before this discovery, `GraphiteBranchManager.create_branch()` contained 18 lines of checkout/restore logic:

1. Save current branch
2. Checkout target branch
3. Run `gt track`
4. Restore original branch

This complexity existed because documentation and examples showed `gt track` being run from the branch being tracked, creating an assumption that checkout was required.

## Correct Pattern

See `RealGraphiteBranchOps.track_branch()` in `packages/erk-shared/src/erk_shared/gateway/graphite/branch_ops/real.py` for the implementation.

The command structure is: `gt track <branch> --parent <parent> --no-interactive`

## Anti-Pattern

Never implement checkout cycles for gt track operations. If you see code that checkouts a branch just to run gt track, it can be simplified.
```

---

#### 2. Update BranchManager abstraction documentation

**Location:** `docs/learned/architecture/branch-manager-abstraction.md`
**Action:** UPDATE
**Source:** [PR #7790]

**Draft Content:**

Update the following sections:

1. **Line 13-14 tripwire**: Remove or revise the tripwire about "calling create_branch() and assuming you're on the new branch" - the behavior has changed now that checkout is not required.

2. **Line 46-47 table row**: Update `GraphiteBranchManager.create_branch()` description from "Creates + tracks via `gt track`, **then restores original branch**" to simply "Creates + tracks via `gt track` using positional syntax". Remove mention of branch restoration.

3. **Line 57**: Remove the paragraph explaining "The restore-after-create behavior exists because `gt track` requires the branch to be checked out."

4. **Lines 72-84**: Simplify the "Graphite create_branch() Complexity" section. Steps 3-4 about temporary checkout and restoration are now obsolete. The method still handles remote-ref parents and auto-fixes diverged parents, but no longer needs checkout cycles.

---

#### 3. Update Branch Manager decision tree

**Location:** `docs/learned/architecture/branch-manager-decision-tree.md`
**Action:** UPDATE
**Source:** [PR #7790]

**Draft Content:**

Remove the "Critical Gotcha: Checkout After Create" section (lines 91-112). This entire section is now obsolete because:

- `gt track` no longer requires checkout
- `create_branch()` no longer performs temporary checkouts
- The anti-pattern example showing "WRONG: Assumes you're on the new branch" is no longer relevant

Replace with a brief historical note:

```markdown
## Historical Note: Checkout Behavior (Pre-PR #7790)

Earlier versions of `GraphiteBranchManager.create_branch()` performed temporary checkouts because `gt track` was believed to require the branch to be checked out. This was resolved when `gt track` positional syntax was discovered. See [gt track Positional Branch Syntax](graphite-track-positional.md).
```

---

#### 4. Update Git and Graphite quirks catalog

**Location:** `docs/learned/architecture/git-graphite-quirks.md`
**Action:** UPDATE
**Source:** [PR #7790]

**Draft Content:**

Update the "Branch Restoration After Graphite Tracking" section (lines 245-260) to indicate this quirk has been resolved:

```markdown
## [RESOLVED] Branch Restoration After Graphite Tracking

**Status**: Resolved in PR #7790

**Previous Behavior**: Graphite's `gt track` command was believed to require the branch to be checked out. `GraphiteBranchManager.create_branch()` implemented save/checkout/track/restore cycles.

**Current Behavior**: `gt track <branch> --parent <parent>` accepts branch names positionally. No checkout required.

**Location in Codebase**: `packages/erk-shared/src/erk_shared/gateway/graphite/branch_ops/real.py`

See [gt track Positional Branch Syntax](graphite-track-positional.md) for details.
```

---

#### 5. Strict metadata schema validation

**Location:** `docs/learned/architecture/metadata-schema-validation.md`
**Action:** CREATE
**Source:** [PR #7790]

**Draft Content:**

```markdown
---
title: "Strict Metadata Schema Validation"
read_when:
  - "adding fields to metadata schemas"
  - "parsing metadata blocks from GitHub issues or PRs"
  - "debugging ValueError from schema validation"
tripwires:
  - action: "adding optional fields to metadata schemas without updating all writers"
    warning: "Schema validation now raises ValueError for unknown fields. All code paths that write metadata must be updated when schemas change."
last_audited: "YYYY-MM-DD HH:MM PT"
audit_result: new
---

# Strict Metadata Schema Validation

## Breaking Change (PR #7790)

Metadata schema classes now raise `ValueError` for unknown fields instead of emitting `warnings.warn()`. This affects 6 schema classes:

- WorktreeCreationSchema
- PlanMetadataSchema
- WorkflowStartedSchema
- PlanRetrySchema
- PlanHeaderSchema
- ObjectiveHeaderSchema

## Why This Change

The previous warning-based approach allowed silent data corruption when:
- Old code wrote fields that new code didn't recognize
- New code added fields that old code would ignore
- Typos in field names went unnoticed

The "fail fast" approach surfaces schema mismatches immediately during development and testing.

## Migration Impact

Code that parses metadata blocks must handle the case where unknown fields may be present from older versions. Consider adding explicit schema versioning or migration paths.

## Source

See `WorktreeCreationSchema.validate()` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py` for the implementation pattern.
```

---

### MEDIUM Priority

#### 6. Admin command OAuth removal

**Location:** `docs/learned/cli/admin-command-changes.md`
**Action:** CREATE
**Source:** [PR #7790]

**Draft Content:**

```markdown
---
title: "Admin Command Breaking Changes"
read_when:
  - "using erk admin gh-actions-api-key command"
  - "configuring GitHub Actions authentication"
  - "migrating from CLAUDE_CODE_OAUTH_TOKEN"
tripwires: []
last_audited: "YYYY-MM-DD HH:MM PT"
audit_result: new
---

# Admin Command Breaking Changes

## erk admin gh-actions-api-key (PR #7790)

### Removed Features

- `--oauth` flag is no longer supported
- `CLAUDE_CODE_OAUTH_TOKEN` management has been removed

### Current Behavior

The command now only manages `ANTHROPIC_API_KEY`. OAuth token management was removed to simplify authentication configuration.

### Migration Path

Users who relied on `--oauth` must:
1. Stop using CLAUDE_CODE_OAUTH_TOKEN
2. Use ANTHROPIC_API_KEY directly for authentication

## Source

See `gh_actions_api_key()` in `src/erk/cli/commands/admin.py`.
```

---

#### 7. Conditional workflow run fetching pattern

**Location:** `docs/learned/performance/lazy-data-loading.md`
**Action:** CREATE
**Source:** [PR #7790]

**Draft Content:**

```markdown
---
title: "Lazy Data Loading Pattern"
read_when:
  - "implementing dashboard or list commands"
  - "optimizing GitHub API call frequency"
  - "adding new data fetching to TUI or CLI"
tripwires: []
last_audited: "YYYY-MM-DD HH:MM PT"
audit_result: new
---

# Lazy Data Loading Pattern

## Pattern Description

Expensive API calls should be conditional based on user-provided flags rather than always fetched. This reduces latency and API rate limit consumption for users who don't need the extra data.

## Implementation Example (PR #7790)

`erk plan list` added `--prs` and `--runs` flags:

- Default: Fast load without workflow runs or detailed PR data
- `--prs`: Include PR status details
- `--runs`: Include workflow run status

The `RealPlanDataProvider.fetch_plans()` method checks `filters.show_runs` before making workflow API calls.

## When to Apply

- Dashboard commands loading multiple data sources
- List commands with optional enrichment columns
- Any operation that makes multiple GitHub API calls

## Source

See `RealPlanDataProvider.fetch_plans()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`.
```

---

#### 8. PlanRowData field changes

**Location:** `docs/learned/tui/data-model-evolution.md`
**Action:** CREATE
**Source:** [PR #7790]

**Draft Content:**

```markdown
---
title: "TUI Data Model Evolution"
read_when:
  - "modifying PlanRowData or related data classes"
  - "updating TUI table tests after schema changes"
  - "adding or removing columns from plan tables"
tripwires: []
last_audited: "YYYY-MM-DD HH:MM PT"
audit_result: new
---

# TUI Data Model Evolution

## PlanRowData Changes (PR #7790)

### Removed Fields

- `pr_has_conflicts`: Boolean for PR conflict state
- `pr_status_display`: String for rendered PR status

### Why Removed

PR status was consolidated into the lifecycle column using emoji suffixes. Separate fields are no longer needed.

### Migration for Tests

Tests that create `PlanRowData` instances must be updated:
- Remove `pr_has_conflicts` and `pr_status_display` from test fixtures
- Update assertions that checked these fields
- PR status is now embedded in `lifecycle_display`

### Test Update Pattern

See `tests/tui/test_plan_table.py` for examples of updated test fixtures (167 additions in PR #7790).

## Source

See `PlanRowData` definition in `src/erk/tui/data/types.py`.
```

---

### LOW Priority

#### 9. PR status emoji conventions

**Location:** `docs/learned/tui/pr-status-indicators.md`
**Action:** CREATE
**Source:** [PR #7790]

**Draft Content:**

```markdown
---
title: "PR Status Emoji Indicators"
read_when:
  - "displaying PR status in TUI"
  - "adding new status indicators to lifecycle column"
tripwires: []
last_audited: "YYYY-MM-DD HH:MM PT"
audit_result: new
---

# PR Status Emoji Indicators

## Emoji Meanings

| Emoji | Meaning            | When Shown                     |
| ----- | ------------------ | ------------------------------ |
| [dr]  | Draft PR           | PR is in draft state           |
| [cf]  | Conflicts          | PR has merge conflicts         |
| [ok]  | Approved           | PR has approving reviews       |
| [ch]  | Changes requested  | PR has change requests         |

## Placement

Emoji indicators appear as suffixes on the lifecycle stage in the plan table lifecycle column. For example: "implementing [cf]" indicates an implementing plan with PR conflicts.

## Source

See `format_lifecycle_with_status()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`.
```

---

#### 10. Lifecycle label conventions

**Location:** `docs/learned/tui/lifecycle-labels.md`
**Action:** CREATE
**Source:** [PR #7790]

**Draft Content:**

```markdown
---
title: "Lifecycle Label Conventions"
read_when:
  - "displaying plan lifecycle stages"
  - "updating lifecycle display text"
tripwires: []
last_audited: "YYYY-MM-DD HH:MM PT"
audit_result: new
---

# Lifecycle Label Conventions

## Design Decision: Full Labels Over Abbreviations (PR #7790)

Changed from abbreviated to full lifecycle labels:

| Before        | After          |
| ------------- | -------------- |
| "impling"     | "implementing" |
| "impld"       | "implemented"  |

## Rationale

Clarity over brevity. Abbreviated labels saved horizontal space but confused users unfamiliar with the conventions. Full labels are self-explanatory.

## Source

See `compute_lifecycle_display()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`.
```

---

#### 11. Plan list command flags

**Location:** `docs/learned/cli/plan-list-flags.md`
**Action:** CREATE
**Source:** [PR #7790]

**Draft Content:**

```markdown
---
title: "Plan List Command Flags"
read_when:
  - "using erk plan list command"
  - "debugging slow plan list performance"
tripwires: []
last_audited: "YYYY-MM-DD HH:MM PT"
audit_result: new
---

# Plan List Command Flags

## Performance Flags (PR #7790)

| Flag     | Effect                           | Default |
| -------- | -------------------------------- | ------- |
| `--prs`  | Include detailed PR status data  | Off     |
| `--runs` | Include workflow run status      | Off     |

## When to Use

- `--prs`: When you need to see review status, conflict state, or approvals
- `--runs`: When you need to see CI/CD workflow status

Without these flags, `erk plan list` loads faster by skipping expensive API calls.

## Source

See `list_cmd.py` in `src/erk/cli/commands/plan/`.
```

---

## Contradiction Resolutions

No contradictions detected. The initial potential contradiction between existing documentation and code implementation was resolved: documentation described manual user workflow (implicit current branch) while code uses programmatic API (explicit positional argument). Both are valid `gt track` invocations in different contexts.

## Stale Documentation Cleanup

No DELETE_STALE actions required. All existing documentation has current references verified. However, three files require updates (addressed in Documentation Items above):

1. `docs/learned/architecture/branch-manager-abstraction.md` - Update to remove checkout/restore references
2. `docs/learned/architecture/branch-manager-decision-tree.md` - Remove obsolete "Critical Gotcha" section
3. `docs/learned/architecture/git-graphite-quirks.md` - Mark "Branch Restoration" section as resolved

## Prevention Insights

No errors or failed approaches were discovered during implementation. The session that implemented PR #7790 executed cleanly without blockers or debugging cycles. The PR had zero human review comments, indicating the implementation matched expectations.

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. gt track positional syntax

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, External tool quirk +1, Repeated pattern +1)
**Trigger:** Before calling gt track with checkout/restore pattern
**Warning:** "FORBIDDEN: Checking out target branch before calling gt track. Use `gt track <branch> --parent <parent>` positional syntax directly."
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because:
- The positional syntax is not documented in gt help or commonly known
- It affects multiple locations: `GraphiteBranchManager.create_branch()`, `retrack_branch()`, and any future gt track usage
- The checkout pattern was embedded in 3 separate code paths totaling 18 lines before removal
- Without this tripwire, agents may re-introduce checkout cycles based on outdated documentation or examples

Recommended tripwire entry format:

> **Before calling gt track with checkout**: FORBIDDEN: Checking out target branch before calling `gt track`. The command accepts branch names positionally: `gt track <branch> --parent <parent>`. Unnecessary checkout/restore cycles add complexity and risk. See docs/learned/architecture/graphite-track-positional.md.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Strict metadata schema validation

**Score:** 3/10 (Cross-cutting +2, Destructive potential +1)
**Notes:** Affects 6 schema classes and will surface immediately during testing. Not tripwire-worthy because it's a deliberate breaking change with clear error messages, not a subtle gotcha. Document as a breaking change but don't add tripwire.

### 2. Conditional workflow run fetching

**Score:** 2/10 (Cross-cutting +2)
**Notes:** Applies to multiple commands but missing the flag just means slower execution, not wrong results. No correctness implications, so not tripwire material.
