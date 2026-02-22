# Documentation Plan: Remove plan review PR feature

## Context

PR #7838 removes the ephemeral plan review PR workflow - a feature that allowed reviewers to add inline comments on plan content before implementation. This is a deletion-only PR that removes a complete feature subsystem including 5 exec scripts, 1 command, 7 test files (~2,400 lines), and comprehensive documentation across 14 files. The feature is being sunset to simplify the planning workflow.

While the PR itself is pure deletion with no new code patterns to document, the implementation session and automated review process surfaced several reusable patterns and prevention insights that warrant documentation. Additionally, the automated bots caught multiple incomplete cleanup items during review, revealing a systematic gap in feature removal practices that should be documented as a checklist.

The most valuable learning from this PR is not about the deleted feature, but about the process: how to systematically remove features while ensuring complete cleanup across code, tests, documentation, workflows, and constants. The bot findings demonstrate that documentation drift during refactoring is a silent failure mode that affects multiple categories.

## Raw Materials

PR #7838 - Remove plan review PR feature

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 5 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 1 |
| Potential tripwires (score 2-3) | 3 |
| Stale documentation items | 0 |

## Documentation Items

### HIGH Priority

#### 1. Feature Removal Checklist

**Location:** `docs/learned/refactoring/feature-removal-checklist.md`
**Action:** CREATE
**Source:** [PR #7838]

**Draft Content:**

```markdown
---
read-when:
  - removing a CLI command or feature
  - deleting a feature subsystem
  - cleaning up deprecated functionality
---

# Feature Removal Checklist

Systematic checklist for completely removing CLI commands and features from erk.

## Why This Matters

Automated bots caught 6+ categories of incomplete cleanup in PR #7838. Feature removal touches many areas and incomplete cleanup leads to:
- Orphaned code and tests
- Documentation referencing deleted features
- Stale schema constants and type unions
- Workflow labels and metadata fields that no longer apply

## Checklist Categories

### Code Removal
- [ ] Delete source files (commands, exec scripts, utilities)
- [ ] Remove function exports and imports
- [ ] Clean up schema constants (e.g., labels, field names)
- [ ] Remove from type unions and discriminated union types
- [ ] Remove integration points (cleanup hooks, event handlers)

### Test Removal
- [ ] Delete test files for removed feature
- [ ] Remove feature-specific test fixtures
- [ ] Update integration tests that reference the feature

### Documentation Removal
- [ ] Delete primary documentation file
- [ ] Remove from index files
- [ ] Update workflow documentation (lifecycle phases, options)
- [ ] Update command reference tables
- [ ] Remove tripwires related to the feature
- [ ] Update tripwire counts in tripwires-index.md

### Metadata Cleanup
- [ ] Remove metadata field handlers (getters, setters, clearers)
- [ ] Remove naming functions (branch names, labels)
- [ ] Check for existing data that needs migration

### Workflow Integration
- [ ] Remove from command group registrations
- [ ] Remove from exit hooks and mode choices
- [ ] Remove cleanup hooks from related commands (land, close, implement)

## Verification Steps

After removal, grep the codebase for:
- Feature name strings (e.g., "review_pr", "plan-review")
- Import statements referencing deleted modules
- Documentation references to removed workflow options
```

---

### MEDIUM Priority

#### 2. Skill vs Task Tool for Fork Execution

**Location:** `docs/learned/planning/agent-execution-modes.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - invoking a skill that needs subagent isolation
  - using --print mode with forked skills
  - deciding between Skill invocation and Task tool
---

# Agent Execution Modes

When to use Task tool vs Skill invocation for forked execution.

## The Problem

Some skills declare `context: fork` metadata expecting to run in an isolated subagent. However, in `--print` mode, this isolation guarantee does not hold - the skill executes in the same context as the parent.

## When to Use Task Tool

Use Task tool instead of Skill invocation when:
- The skill needs true context isolation (separate tools, state)
- Running in `--print` mode where fork isolation is not enforced
- The command instructions explicitly require Task tool

## Example: pr-feedback-classifier

The pr-feedback-classifier skill must be invoked via Task tool because its classification logic depends on isolation from the parent agent's context. Direct Skill invocation in `--print` mode may produce inconsistent results.

## Key Insight

Skill metadata `context: fork` is a hint to the runtime, not a guarantee. Command authors should document explicit tool requirements when isolation matters.
```

---

#### 3. Preview Command Pattern

**Location:** `docs/learned/commands/preview-command-pattern.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - creating read-only preview commands
  - designing command pairs (preview + action)
  - implementing inspection commands
---

# Preview Command Pattern

Template for read-only preview commands that display information without taking action.

## Pattern Overview

Preview commands fetch data, analyze it, and display a summary. They explicitly forbid all actions to maintain read-only semantics.

## Structure

1. **Data Fetching**: Call APIs or exec commands to gather current state
2. **Analysis/Classification**: Process data (e.g., classify PR comments)
3. **Display Summary**: Show formatted results to user
4. **Explicit Forbidding**: End with clear prohibitions

## Explicit Action Forbidding

Preview commands should end with explicit prohibitions:

> **STOP. Do NOT take any action:**
> - Do NOT modify code
> - Do NOT resolve threads
> - Do NOT reply to comments
> - Do NOT create commits
> - Do NOT push changes
>
> Only display information. User will run the action command separately.

## Example: /erk:pr-preview-address

See `.claude/commands/erk/pr-preview-address.md` for implementation.

## Benefits

- Clear separation of concerns (read vs write)
- User maintains control over actions
- Reduces accidental modifications
- Enables time-gap scenarios where state may change between preview and action
```

---

#### 4. PR Feedback Classification Model

**Location:** `docs/learned/pr-operations/feedback-classification.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - classifying PR review comments
  - ordering batch processing of review threads
  - implementing PR address workflows
---

# PR Feedback Classification Model

Schema for classifying PR review comments to determine processing order and action type.

## Classification Dimensions

### Action Type
- **actionable**: Code changes needed - agent should modify files
- **informational**: User decides to act or dismiss - no automatic code changes

### Complexity Levels
Determines batch ordering for actionable items:
1. **local**: Changes confined to single location
2. **multi-location**: Changes span multiple locations in same file
3. **cross-cutting**: Changes span multiple files
4. **complex/related**: Changes depend on other changes or require careful ordering

## Batch Processing Order

Process actionable items in complexity order:
1. Local changes first (least risk of conflicts)
2. Multi-location changes
3. Cross-cutting changes
4. Complex/related changes last (may depend on earlier changes)

## Verification Pattern

When classifier results seem inconsistent:
1. Re-run with more capable model (Sonnet over Haiku)
2. Verify directly with source command (e.g., `erk exec get-pr-review-comments`)
3. Consider time-gap scenarios where state may have changed
```

---

#### 5. Model Selection Guidance for Classifiers

**Location:** `docs/learned/architecture/model-selection-guidance.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - choosing models for classification tasks
  - debugging classifier inconsistencies
  - implementing automated analysis
---

# Model Selection Guidance

When to use different models for classification tasks and how to verify results.

## Model Capabilities

### Haiku (Fast, Cost-Effective)
- Simple classification tasks
- High-volume, low-stakes decisions
- Initial pass before escalation

### Sonnet (Balanced)
- Critical classification tasks
- Verification of Haiku results
- Tasks requiring nuanced understanding

## Verification Pattern

When classifier results seem incorrect or inconsistent:

1. **Escalate model**: Re-run with more capable model
2. **Direct verification**: Query source data directly to confirm
3. **Time-gap check**: Consider if state changed between operations

## Example: PR Feedback Classification

Session showed Haiku returning empty results when preview showed 1 thread.

Investigation steps:
1. Re-ran with Sonnet - also returned empty
2. Verified with `erk exec get-pr-review-comments` - confirmed 0 threads
3. Conclusion: Thread was resolved between preview and address (time gap)

## Key Insight

Classifier discrepancies may indicate real state changes, not model failures. Always verify with direct commands before assuming model error.
```

---

### LOW Priority

None. All items are HIGH or MEDIUM priority.

## Contradiction Resolutions

**None detected.** This is a deletion-only PR. All documentation about the removed feature has been cleaned up within the PR itself.

## Stale Documentation Cleanup

**All stale documentation has already been removed in PR #7838.**

The PR properly cleaned up:
- `docs/learned/planning/pr-review-workflow.md` (deleted)
- `docs/learned/planning/lifecycle.md` (Phase 2b removed)
- `docs/learned/planning/workflow.md` (Option E removed)
- `docs/learned/planning/workflow-markers.md` (review markers removed)
- `.claude/commands/erk/plan-review.md` (deleted)
- `.claude/skills/erk-exec/SKILL.md` (4 commands removed)
- `.claude/skills/erk-exec/reference.md` (3 exec docs removed)
- `docs/learned/cli/erk-exec-commands.md` (2 sections removed)
- `docs/learned/planning/tripwires.md` (6 lines removed)
- `docs/learned/tripwires-index.md` (count updated)

### Additional Verification Needed

The gap analysis flagged three documents for manual verification:

1. **`docs/learned/architecture/plan-file-sync-pattern.md`**: Check if pattern is used only for removed feature. If review-only, archive. If used elsewhere, update examples.

2. **`docs/learned/architecture/metadata-archival-pattern.md`**: Check if document uses `review_pr`/`last_review_pr` as examples. If yes, replace with different example.

3. **`docs/learned/glossary.md`**: Check for "review PR" or "plan review PR" term definitions. If present, remove those definitions.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Classifier Returning Stale/Incorrect Data

**What happened:** Haiku classifier returned 0 actionable threads when preview showed 1 thread.

**Root cause:** Time gap between preview and address commands. The thread was resolved by another process between the two operations.

**Prevention:** Always verify classifier results with direct commands when discrepancy suspected. Use more capable models for critical classification tasks.

**Recommendation:** ADD_TO_DOC (covered in model-selection-guidance.md)

### 2. Incomplete Feature Removal

**What happened:** Automated bots caught 6+ categories of incomplete cleanup during PR review: private symbol names in docs, inaccurate behavior claims, stale sections, default parameters in code, schema constants, workflow field names.

**Root cause:** No systematic checklist for feature removal. Each cleanup area was discovered reactively during bot review.

**Prevention:** Use feature removal checklist before declaring PR complete. Run grep for feature-related strings across entire codebase.

**Recommendation:** ADD_TO_DOC (covered in feature-removal-checklist.md) + TRIPWIRE (documentation drift)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Documentation Drift During Refactoring

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)

**Trigger:** Before merging a PR that refactors field names, workflow inputs, or removes features

**Warning:** "grep docs/ for old names and update ALL references including flow diagrams, tables, and narrative sections"

**Target doc:** `docs/learned/documentation/tripwires.md`

This is tripwire-worthy because the failure mode is completely silent - no tests fail, no linting errors occur. The bots caught documentation referencing old field names (`issue_number`/`issue_title` vs `plan_id`/`plan_title`), removed features in flow diagrams, and stale narrative sections. Without automated checking, these inconsistencies persist indefinitely and confuse future agents.

## Potential Tripwires

Items with score 2-3 (may warrant tripwire status with additional context):

### 1. Incomplete Feature Removal

**Score:** 3/10 (criteria: Cross-cutting +2, Repeated pattern +1)

**Notes:** Bot caught schema constants, type unions, orphaned tests. The feature removal checklist document may be sufficient instead of a tripwire. Could be promoted if pattern repeats in future removal PRs.

### 2. Skill vs Task for Fork Execution

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)

**Notes:** Specific to Claude Code `--print` mode behavior. Better as pattern documentation than tripwire since it applies to specific command authoring scenarios, not general development.

### 3. Batch Thread Resolution Preference

**Score:** 2/10 (criteria: Efficiency improvement +1, Documented in command +1)

**Notes:** Preference for `erk exec resolve-review-threads` (batch) over `erk exec resolve-review-thread` (single). Already documented in command instructions. Low value as tripwire since command design enforces the pattern.
