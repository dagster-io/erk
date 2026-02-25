# Document PR-only roadmap model and deterministic re-rendering

## Context

PR #8128 represents a significant architectural simplification of erk's objective roadmap system. The core change replaces the previous dual-storage model (where YAML frontmatter and markdown tables could be mutated independently) with a single-source-of-truth model where YAML is authoritative and tables are always deterministically re-rendered. The `plan` field has been entirely removed from `RoadmapNode` and `ObjectiveNode` dataclasses, reducing status inference to a simpler 3-case logic (explicit status > PR-based inference > preserve existing).

This documentation effort matters because the change touches fundamental concepts that agents interact with daily: roadmap node structure, status inference rules, and CLI command signatures. Without accurate documentation, future agents will document behavior based on outdated mental models, leading to the systematic drift patterns already observed in PR review (6 threads caught incorrect status inference documentation).

Key insights include: (1) the new `rerender_comment_roadmap()` function eliminates fragile per-node regex patching in favor of atomic full-table regeneration; (2) workflows that relied on automatic plan-based node matching must now pass explicit `--node` flags; (3) existing tripwires about plan preservation are now obsolete and have been removed. The PR already updated 9 documentation files and deleted 1 (plan-reference-preservation.md), but PR review revealed gaps in accuracy that must be addressed.

## Raw Materials

PR #8128: Simplify objective roadmap to single-reference (PR-only) model with deterministic re-rendering

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 24    |
| Contradictions to resolve      | 3     |
| Tripwire candidates (score>=4) | 8     |
| Potential tripwires (score2-3) | 4     |

## Contradiction Resolutions

Resolve these BEFORE creating new documentation:

### 1. Dual-Storage to Single-Reference Model

**Existing doc:** `docs/learned/architecture/roadmap-mutation-semantics.md`
**Conflict:** Existing guidance refers to "writes both cells atomically" and maintaining dual storage (YAML + markdown) independently. PR #8128 fundamentally changes this to single-source-of-truth.
**Resolution:** Verify the PR's updates to this file correctly removed dual-storage language. Document the new `rerender_comment_roadmap()` function that replaces fragile per-node regex patching.

### 2. 5-Column to 4-Column Table Format

**Existing doc:** Multiple files (`roadmap-format-versioning.md`, `roadmap-parser.md`, `roadmap-parser-api.md`)
**Conflict:** Existing guidance shows `| Node | Description | Status | Plan | PR |` as the canonical format. PR removed the Plan column entirely.
**Resolution:** Update all roadmap documentation to show 4-column format: `| Node | Description | Status | PR |`. Update YAML examples to remove `plan` field. Verify schema version is now v4.

### 3. Plan Reference Preservation (Obsolete)

**Existing doc:** `docs/learned/objectives/plan-reference-preservation.md` (was 86 lines)
**Conflict:** This document described defense-in-depth patterns for preserving plan references when updating PR references.
**Resolution:** Already deleted in PR #8128 - this is a positive example of stale doc cleanup. No further action needed.

## Stale Documentation Cleanup

**Status:** CLEAN - The PR correctly removed `docs/learned/objectives/plan-reference-preservation.md` when removing plan field support. ExistingDocsChecker verified all other referenced files exist.

## Documentation Items

### HIGH Priority

#### 1. Document deterministic re-rendering pattern

**Location:** `docs/learned/architecture/roadmap-mutation-semantics.md`
**Action:** UPDATE
**Source:** [PR #8128]

**Draft Content:**

```markdown
## Deterministic Re-rendering

### The Pattern

Roadmap comment tables are now deterministically re-rendered from YAML frontmatter after every mutation. See `rerender_comment_roadmap()` in roadmap.py for the implementation.

### Why This Matters

The previous approach used per-node regex replacement, which was fragile and could produce inconsistent results when multiple nodes changed simultaneously. The new approach:

1. Mutates YAML frontmatter (single source of truth)
2. Re-renders the entire comment body including all tables
3. Updates the comment atomically

### Key Functions

- `rerender_comment_roadmap()`: Orchestrates the full re-render from YAML to comment body
- `update_node_in_frontmatter()`: Mutates a single node in YAML frontmatter

### Implementation Notes

See packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py for implementation details.
```

---

#### 2. Update RoadmapNode dataclass documentation

**Location:** `docs/learned/objectives/roadmap-parser-api.md`
**Action:** UPDATE
**Source:** [PR #8128]

**Draft Content:**

```markdown
## RoadmapNode Dataclass

The `RoadmapNode` frozen dataclass represents a single node in an objective's roadmap:

### Fields (v4 schema)

- `id`: Unique node identifier (e.g., "1", "1.1", "2")
- `description`: Human-readable description of the step
- `status`: Current status (pending, in_progress, done, blocked)
- `pr`: Optional PR reference (e.g., "#123")
- `depends_on`: Optional list of node IDs this step depends on

Note: The `plan` field was removed in schema v4. Roadmaps now track only PR references.

See packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py for the dataclass definition.
```

---

#### 3. Verify and update status inference documentation

**Location:** `docs/learned/objectives/roadmap-status-system.md`
**Action:** UPDATE
**Source:** [PR #8128]

**Draft Content:**

```markdown
## Status Inference Rules

Status inference follows a 3-case priority order:

1. **Explicit status**: If `--status` is provided, use it directly
2. **PR-based inference**: If `--pr #123` is provided (non-empty), infer `in_progress`
3. **Preserve existing**: Otherwise, keep the current status

### Common Misconception

Setting `--pr #123` infers `in_progress`, NOT `done`. The `done` status must be set explicitly using `--status done`.

### Field Clearing

Using `--pr ""` (empty string) clears the PR field but preserves the existing status. It does NOT reset status to `pending`.

See `update_node_in_frontmatter()` in roadmap.py for implementation.
```

---

#### 4. Update roadmap table format documentation

**Location:** `docs/learned/objectives/roadmap-format-versioning.md`
**Action:** UPDATE
**Source:** [PR #8128]

**Draft Content:**

```markdown
## Version 4 Table Format

Schema v4 (current) uses a 4-column format:

| Node | Description | Status | PR |
|------|-------------|--------|-----|
| 1    | First step  | done   | #100 |
| 2    | Second step | in_progress | #101 |

### Changes from v3

- Removed "Plan" column - roadmaps now track only PR references
- `plan` field removed from YAML frontmatter nodes
- All plan-based status inference logic removed

### Migration

Existing objectives with plan-only nodes will lose that data when updated. Workflows must be updated to use explicit `--node` flags instead of automatic plan-based matching.
```

---

#### 5. Document explicit node selection requirement

**Location:** `docs/learned/objectives/objective-lifecycle.md`
**Action:** UPDATE
**Source:** [PR #8128]

**Draft Content:**

```markdown
## Node Selection for Updates

The `objective-apply-landed-update` command requires explicit `--node` flags to identify which roadmap nodes to update. Automatic plan-based matching is no longer supported.

### Example Usage

```bash
erk exec objective-apply-landed-update --objective 123 --pr 456 --node 1.1 --node 1.2
```

### Why Explicit Selection

The previous automatic matching used plan references to find nodes, which:
- Created implicit dependencies on plan field data
- Made it difficult to debug why certain nodes were or weren't matched
- Added complexity to the status inference logic

Explicit selection follows the "explicit over implicit" principle.
```

---

#### 6. Document removed matched_steps from context

**Location:** `docs/learned/objectives/objective-lifecycle.md`
**Action:** UPDATE
**Source:** [PR #8128]

**Draft Content:**

```markdown
## Objective Context Output

The `objective-fetch-context` command returns context about an objective for use by skills and commands. Note that the `matched_steps` field has been removed as of the PR-only model transition.

### Current Context Fields

The context output includes objective metadata, roadmap phases, and current node statuses. See the command output for the current schema.

### Migration Note

Workflows that relied on `matched_steps` for automatic node selection must now use explicit `--node` flags with `objective-apply-landed-update`.
```

---

#### 7. Add status inference verification tripwire

**Location:** `docs/learned/objectives/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [PR #8128]

**Draft Content:**

```markdown
## Status Inference Verification

**Trigger:** Before documenting status inference behavior for objective roadmap nodes

**Warning:** Verify against `update_node_in_frontmatter()` source code. PR references infer `in_progress`, not `done`. Don't document from memory - check actual status inference logic.

**Why:** PR review caught 6 instances where documentation incorrectly claimed `--pr #123` infers `done`. The actual behavior is `in_progress` inference.
```

---

#### 8. Add required parameter verification tripwire

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [PR #8128]

**Draft Content:**

```markdown
## Required Parameter Verification

**Trigger:** Before documenting CLI command usage examples with Click commands

**Warning:** Verify Click parameter requirements. Check for `required=True` flags in command definition before showing standalone usage. A parameter marked `required=True` cannot appear in standalone examples without its dependencies.

**Why:** Documentation showed invalid command patterns where required parameters were missing.
```

---

### MEDIUM Priority

#### 9. Strengthen private function reference tripwire

**Location:** `docs/learned/documentation/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8128]

**Draft Content:**

```markdown
## Private Function References

**Trigger:** Before writing documentation or test docstrings that reference implementation details

**Warning:** Private `_underscore` methods NEVER appear in docs OR test docstrings. Reference public APIs only. Describe behavior using public function names, or explain the concept without naming specific private functions.

**Why:** 3 PR review threads caught private function names in documentation despite existing guidance. This tripwire strengthens the prohibition to explicitly include test docstrings.
```

---

#### 10. Add function name verification best practice

**Location:** `docs/learned/documentation/learned-docs-core.md`
**Action:** UPDATE
**Source:** [PR #8128]

**Draft Content:**

```markdown
## Function Name Verification

When documenting function calls, verify imports and actual usage in source files. Don't assume function names from memory.

### Verification Steps

1. Grep the source file for the function name you plan to document
2. Check the import statements to confirm the public API name
3. Verify the function signature matches what you're documenting

### Example Error

Documentation referenced `parse_roadmap_frontmatter()` but the actual function is `parse_roadmap()`. This was caught in PR review.
```

---

#### 11. Add field clearing behavior tripwire

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [PR #8128]

**Draft Content:**

```markdown
## Field Clearing Behavior

**Trigger:** Before documenting field clearing with empty string values

**Warning:** Verify the actual status inference logic. Check if status is preserved vs reset when clearing fields. Empty string (`""`) may preserve existing status rather than resetting to default.

**Why:** Documentation claimed `--pr ""` resets status to `pending`, but it actually preserves existing status.
```

---

#### 12. Add operation description quality check

**Location:** `docs/learned/documentation/learned-docs-core.md`
**Action:** UPDATE
**Source:** [PR #8128]

**Draft Content:**

```markdown
## Operation Description Quality

Step-by-step operation descriptions must be coherent. If mentioning implementation details, separate "what happens" from "how it's implemented".

### Pattern to Avoid

"The command calls `_internal_func()` which updates the thing."

### Better Pattern

"The command updates the node status. The implementation is in `update_node_in_frontmatter()`."

This separates the user-facing behavior from implementation mechanics.
```

---

#### 13. Add lifecycle workflow verification tripwire

**Location:** `docs/learned/objectives/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [PR #8128]

**Draft Content:**

```markdown
## Lifecycle Workflow Verification

**Trigger:** Before documenting objective lifecycle workflows

**Warning:** Verify against actual command files in `.claude/commands/`. Don't document inferred behavior without checking implementation. Command usage patterns evolve; docs must reflect current state.

**Why:** PR review caught stale command usage patterns that no longer matched actual command files.
```

---

#### 14. Add field removal documentation grep tripwire

**Location:** `docs/learned/refactoring/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [PR #8128]

**Draft Content:**

```markdown
## Field Removal Documentation Grep

**Trigger:** Before removing fields from dataclasses or schemas

**Warning:** Grep all docs for references to the removed field name. Check: (1) YAML examples, (2) prose descriptions, (3) data flow diagrams, (4) CLI command documentation showing the field flag.

**Why:** PR #8128 removed the `plan` field, and multiple doc sections still referenced it despite the field being gone from code.
```

---

#### 15. Add command rename documentation grep tripwire

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [PR #8128]

**Draft Content:**

```markdown
## Command Rename Documentation Grep

**Trigger:** Before renaming CLI commands

**Warning:** Grep all docs for old command name. Check: (1) explicit command references, (2) code examples, (3) workflow descriptions in lifecycle docs, (4) slash command files that invoke the command.

**Why:** Documentation referenced `update-roadmap-step` when the command was actually `update-objective-node`.
```

---

#### 16. Document Task tool for skill fork isolation

**Location:** `docs/learned/claude-code/skill-execution-patterns.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Skill Execution Patterns
category: claude-code
read-when:
  - invoking skills with context: fork metadata
  - running pr-feedback-classifier or similar forked skills
tripwires: 1
---

# Skill Execution Patterns

## Task Tool for Fork Isolation

When invoking skills that have `context: fork` metadata, use the Task tool instead of direct Skill tool invocation.

### Why This Matters

The `context: fork` metadata is intended to create subagent isolation, but in `--print` mode this isolation is not guaranteed. The Task tool provides explicit subagent execution that guarantees the skill runs in a separate context.

### Example Pattern

The `/erk:pr-address` command uses this pattern for `pr-feedback-classifier`:

```
# Instead of: Skill(skill="pr-feedback-classifier")
# Use: Task tool with explicit skill loading
```

### When to Use

Use Task tool invocation when:
- The skill has `context: fork` metadata
- You need guaranteed isolation from the parent context
- The skill performs classification or analysis that should not affect parent state
```

---

#### 17. Document CI failure triage for doc-only changes

**Location:** `docs/learned/ci/documentation-pr-ci-triage.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: CI Triage for Documentation PRs
category: ci
read-when:
  - CI fails after documentation-only changes
  - encountering workspace infrastructure errors on doc PRs
tripwires: 1
---

# CI Triage for Documentation PRs

## Identifying Pre-existing Failures

Documentation-only changes (markdown edits, YAML frontmatter updates) cannot cause Python workspace failures. When CI fails after doc-only changes:

### Triage Steps

1. Check if the error is related to any changed files
2. For workspace errors (missing pyproject.toml, import failures), identify as pre-existing
3. For infrastructure errors unrelated to changed files, proceed with commit

### Example Pre-existing Error

```
Error: packages/erk-slack-bot missing pyproject.toml
```

This workspace configuration issue exists independent of documentation changes and should not block the commit.

### When to Block

Block only when CI errors are directly related to the files changed in the PR.
```

---

#### 18. Verify slash command updates completeness

**Location:** Multiple `.claude/commands/erk/` files
**Action:** UPDATE (verification)
**Source:** [PR #8128]

**Draft Content:**

Verify the following slash commands were correctly updated in PR #8128:

- `/erk:objective-update-with-closed-plan`: Now uses `--pr ""` instead of `--plan ""`
- `/erk:objective-update-with-landed-pr`: Requires explicit `--node` flags
- `/erk:plan-save`: Uses `--pr "" --status in_progress` instead of `--plan`
- `/local:objective-reevaluate`: Removed plan preservation requirement

Read each file and verify the changes match the PR-only model.

---

### LOW Priority

#### 19. Update ObjectiveNode dataclass documentation

**Location:** `docs/learned/objectives/dependency-graph.md`
**Action:** UPDATE
**Source:** [PR #8128]

**Draft Content:**

```markdown
## ObjectiveNode Dataclass

The `ObjectiveNode` class represents a node in the dependency graph. The `plan` field has been removed as of schema v4.

### Current Fields

See packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py for the current dataclass definition.
```

---

#### 20. Verify roadmap-mutation-patterns.md completeness

**Location:** `docs/learned/objectives/roadmap-mutation-patterns.md`
**Action:** UPDATE (verification)
**Source:** [PR #8128]

**Draft Content:**

Verify the PR's rewrite correctly reflects the PR-only model. Check for any remaining references to plan fields or dual-storage patterns.

---

#### 21. Verify objective-lifecycle.md completeness

**Location:** `docs/learned/objectives/objective-lifecycle.md`
**Action:** UPDATE (verification)
**Source:** [PR #8128]

**Draft Content:**

Verify the PR's updates correctly reflect the PR-only model and removed `matched_steps`. Ensure lifecycle descriptions match current command behavior.

---

#### 22. Verify objective-roadmap-check.md completeness

**Location:** `docs/learned/objectives/objective-roadmap-check.md`
**Action:** UPDATE (verification)
**Source:** [PR #8128]

**Draft Content:**

Verify updated validation rules correctly reflect the removed plan field. Ensure validation examples show current field expectations.

---

#### 23. Update schema reference documentation

**Location:** `docs/learned/reference/` (if schema docs exist)
**Action:** UPDATE
**Source:** [PR #8128]

**Draft Content:**

```markdown
## Roadmap Schema v4

Version 4 of the roadmap schema removes the `plan` field from node definitions.

### Node Schema

```yaml
nodes:
  - id: "1"
    description: "Step description"
    status: pending | in_progress | done | blocked
    pr: "#123"  # optional
    depends_on: ["other-node-id"]  # optional
```

Note: The `plan` field is no longer valid in v4 schema.
```

---

#### 24. Verify click-framework-conventions.md reference

**Location:** `docs/learned/cli/click-framework-conventions.md`
**Action:** UPDATE (verification)
**Source:** [PR #8128]

**Draft Content:**

Verify the reference update from `plan-reference-preservation.md` to `roadmap-mutation-semantics.md` is correct and contextually appropriate.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Status Inference Documentation Drift

**What happened:** 6 PR review threads flagged documentation claiming `--pr #123` infers `done` status.
**Root cause:** Documentation was written based on assumed behavior rather than verified source code.
**Prevention:** Always verify status inference rules against `update_node_in_frontmatter()` source code before documenting.
**Recommendation:** TRIPWIRE (added as item #7)

### 2. Private Function References in Docs

**What happened:** 3 PR review threads caught private `_underscore` function names in documentation prose.
**Root cause:** Existing tripwire wasn't strong enough - didn't explicitly cover test docstrings.
**Prevention:** Strengthen tripwire to explicitly forbid private functions in ALL documentation contexts including test docstrings.
**Recommendation:** TRIPWIRE (added as item #9)

### 3. Pre-existing CI Failures Blocking Commits

**What happened:** `make fast-ci` failed with missing `pyproject.toml` in `packages/erk-slack-bot`.
**Root cause:** Pre-existing workspace configuration issue unrelated to documentation changes.
**Prevention:** For documentation-only PRs, triage CI failures by checking relationship to changed files.
**Recommendation:** ADD_TO_DOC (added as item #17)

### 4. Incomplete Field Removal Grep

**What happened:** Multiple documentation sections still referenced `plan` field after it was removed from code.
**Root cause:** Did not grep all docs for field name references before removing field.
**Prevention:** Before removing any dataclass field, grep all docs for that field name.
**Recommendation:** TRIPWIRE (added as item #14)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Status Inference Verification

**Score:** 8/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2, Repeated pattern +1, External tool quirk +1)
**Trigger:** Before documenting status inference behavior for objective roadmap nodes
**Warning:** Verify against `update_node_in_frontmatter()` source code. PR references infer `in_progress`, not `done`. Don't document from memory - check actual status inference logic.
**Target doc:** `docs/learned/objectives/tripwires.md`

This pattern appeared 6 times in a single PR review. The behavior is non-obvious (many would assume PR presence means "done") and documentation drift occurs silently since there's no automated check.

### 2. Required Parameter Verification

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before documenting CLI command usage examples with Click commands
**Warning:** Verify Click parameter requirements. Check for `required=True` flags in command definition before showing standalone usage.
**Target doc:** `docs/learned/cli/tripwires.md`

Documentation showed invalid command patterns where required parameters were missing, leading to examples that would fail if executed.

### 3. Field Clearing Behavior

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before documenting field clearing with empty string values
**Warning:** Verify the actual status inference logic. Check if status is preserved vs reset when clearing fields.
**Target doc:** `docs/learned/cli/tripwires.md`

The difference between "clears field and preserves status" vs "clears field and resets status" is significant but not obvious from the API.

### 4. Field Removal Documentation Grep

**Score:** 7/10 (criteria: Non-obvious +2, Cross-cutting +2, Repeated pattern +1, Destructive potential +2)
**Trigger:** Before removing fields from dataclasses or schemas
**Warning:** Grep all docs for references to the removed field name. Check YAML examples, prose descriptions, data flow diagrams, CLI command flags.
**Target doc:** `docs/learned/refactoring/tripwires.md`

Breaking changes require comprehensive documentation updates. Missing a reference creates stale documentation that confuses future agents.

### 5. Lifecycle Workflow Verification

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before documenting objective lifecycle workflows
**Warning:** Verify against actual command files in `.claude/commands/`. Don't document inferred behavior.
**Target doc:** `docs/learned/objectives/tripwires.md`

Command workflows evolve independently of their documentation. Verification prevents documenting stale patterns.

### 6. Command Rename Documentation Grep

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before renaming CLI commands
**Warning:** Grep all docs for old command name in explicit references, code examples, and workflow descriptions.
**Target doc:** `docs/learned/cli/tripwires.md`

Renamed commands leave orphaned references that cause confusion when agents try to execute documented examples.

### 7. Private Function Reference Strengthening

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Repeated pattern +1, Destructive potential +1)
**Trigger:** Before writing documentation or test docstrings that reference implementation details
**Warning:** Private `_underscore` methods NEVER appear in docs OR test docstrings. Reference public APIs only.
**Target doc:** `docs/learned/documentation/tripwires.md`

Despite existing guidance, this pattern recurred because the tripwire wasn't explicit about test docstrings.

### 8. Pre-existing CI Failure Triage

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2)
**Trigger:** When encountering CI failures after making documentation-only changes
**Warning:** Documentation-only changes cannot cause Python workspace failures. If CI fails with infrastructure issues, identify as pre-existing and proceed.
**Target doc:** `docs/learned/ci/tripwires.md`

Prevents blocking commits on unrelated infrastructure issues.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Function Name Verification

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** Only two instances in PR review, may not be cross-cutting enough for a tripwire. Better as a best practice in learned-docs-core.md.

### 2. Operation Description Quality

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** Single instance of garbled description mixing function names with operations. Worth documenting as best practice but not tripwire-worthy.

### 3. Task Tool for Fork Isolation

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** Specific to Claude Code `context: fork` metadata behavior. Narrow applicability but important for skill execution patterns.

### 4. CI Failure Triage for Doc Changes

**Score:** 3/10 (criteria: Non-obvious +2, Cross-cutting +1)
**Notes:** Specific to documentation-only PRs. May warrant tripwire status if pattern recurs.
