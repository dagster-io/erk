# Documentation Plan: Consolidate objective update workflow into single exec command

## Context

This plan captured learnings from PR #8069, which consolidated the `/erk:objective-update-with-landed-pr` workflow from 7 sequential agent commands into 3 streamlined steps. The core innovation was creating a single `objective-apply-landed-update` exec script that bundles all mechanical operations (fetch context, update roadmap nodes, post action comment), leaving only prose reconciliation work to the orchestrating agent.

The implementation demonstrated a reusable **sequential command consolidation pattern**: identify multi-step workflows where the agent performs deterministic work (YAML parsing, JSON construction, sequential API calls) with no LLM judgment between steps, then bundle those operations into a single atomic Python exec script. This pattern reduced the slash command from ~150 lines to ~70 lines while moving testable logic into Python.

Several recoverable errors during implementation revealed tripwire-worthy patterns: Time gateway API mismatches, optional discovery path edge cases, and missing steps in the exec command addition checklist. These patterns apply broadly across erk development and warrant documentation to prevent future agents from repeating the same mistakes.

## Raw Materials

PR #8069 - Session materials available in `.erk/scratch/sessions/d0ded98f-3fe7-490b-9e14-b810dc39d3e8/learn-agents/`

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 7     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Optional Discovery Path Edge Cases Tripwire

**Location:** `docs/learned/objectives/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] session-46dd5570-part2 (Error 2)

**Draft Content:**

```markdown
## Optional Discovery Flags Create None Values

**When:** Adding `--flag` parameter to discovery commands like `objective-fetch-context` that shortcuts normal discovery flow

**Check:** Audit ALL downstream logic that consumes discovered values. When a shortcut flag bypasses normal discovery:
- Values that would normally be populated may be `None`
- Error messages must indicate which flags are required when shortcuts are used
- LBYL pattern: check for `None` before using discovered values

**Example:** The `--plan` flag on `objective-fetch-context` bypasses branch-based discovery. When `--plan` is provided but `--branch` is not, `branch_name` is `None` and PR discovery fails unless `--pr` is also provided.

**Related doc:** See `src/erk/cli/commands/exec/scripts/objective_fetch_context.py` for the implementation pattern.
```

---

#### 2. Time Gateway API Mismatch Tripwire

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] session-46dd5570-part2 (Error 1)

**Draft Content:**

```markdown
## Gateway APIs Differ From Stdlib

**When:** Using gateway methods (Time, Git, GitHub, Shell) in exec scripts

**Check:** Always check the ABC definition before calling gateway methods. Gateway APIs intentionally differ from stdlib equivalents:
- `Time.now()` does NOT accept a `tz` parameter (unlike `datetime.now(tz=...)`)
- Use `time.now().strftime("%Y-%m-%d")` for date formatting
- Other gateways may have similar intentional divergences

**Prevention:** Read the ABC signature in `src/erk/gateway/` before assuming a method exists or accepts certain parameters.

**Example error:** `time.now(tz=timezone.utc)` fails because the Time ABC only supports `now()` with no parameters.
```

---

#### 3. Exec Command Addition Checklist Tripwire

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] session-46dd5570-part2 (Error 3), session-46dd5570-part3

**Draft Content:**

```markdown
## Exec Command Addition Checklist

**When:** Creating a new file in `src/erk/cli/commands/exec/scripts/`

**Required steps (in order):**
1. Create the exec script with `@click.command(name="kebab-case")`
2. Create TypedDict for result structure in `packages/erk-shared/src/erk_shared/` (if complex output)
3. Add import and registration in `src/erk/cli/commands/exec/group.py`
4. Write comprehensive tests (happy path + error cases)
5. Run `erk-dev gen-exec-reference-docs` to update `.claude/skills/erk-exec/reference.md`
6. Run `prettier --write` on any modified `.claude/commands/` files

**CI will fail if you skip steps 5 or 6.** The reference docs are auto-maintained but require manual regeneration. Prettier is enforced on all command files.
```

---

### MEDIUM Priority

#### 4. TypedDict Schema for objective-apply-landed-update

**Location:** `docs/learned/reference/objective-apply-landed-update-schema.md`
**Action:** CREATE
**Source:** [Impl] diff analyzer

**Draft Content:**

```markdown
---
read-when:
  - consuming output from objective-apply-landed-update exec script
  - working with objective update JSON schemas
tripwires: 0
---

# objective-apply-landed-update JSON Schema

The `erk exec objective-apply-landed-update` command outputs structured JSON consumed by `/erk:objective-update-with-landed-pr`. This document describes the schema as defined in `packages/erk-shared/src/erk_shared/objective_apply_landed_update_result.py`.

## Schema Overview

The command returns one of two shapes:

### Success Response

```json
{
  "success": true,
  "objective": { /* ObjectiveFetchContextResultDict */ },
  "plan": { /* plan info */ },
  "pr": { /* PR info */ },
  "roadmap": {
    "matched_steps": ["node-id-1", "node-id-2"],
    "all_complete": false,
    "next_node": "node-id-3"
  },
  "node_updates": [
    {
      "node_id": "node-id-1",
      "previous_status": "in-progress",
      "previous_plan": null,
      "previous_pr": null
    }
  ],
  "action_comment_id": 12345
}
```

### Error Response

```json
{
  "success": false,
  "error": "Error message",
  "error_code": "OBJECTIVE_NOT_FOUND"
}
```

## TypedDict Definitions

See `packages/erk-shared/src/erk_shared/objective_apply_landed_update_result.py` for the canonical type definitions:
- `ApplyLandedUpdateResultDict` - success response
- `ApplyLandedUpdateErrorDict` - error response
- `NodeUpdateDict` - individual node update record

## Usage Pattern

Calling commands parse the JSON and use `node_updates` for audit trail, `roadmap.next_node` to identify remaining work, and `objective.objective_content` for prose reconciliation.
```

---

#### 5. Exec Script Consolidation Pattern

**Location:** `docs/learned/objectives/apply-landed-update-exec-script.md`
**Action:** CREATE
**Source:** [Impl] all sessions, diff analyzer

**Draft Content:**

```markdown
---
read-when:
  - considering consolidating multiple sequential agent commands
  - working on objective-apply-landed-update or similar workflows
tripwires: 0
---

# Exec Script Consolidation Pattern: objective-apply-landed-update

This document describes the consolidation pattern demonstrated by the `objective-apply-landed-update` exec script, which reduced `/erk:objective-update-with-landed-pr` from 7 steps to 3 steps.

## The Problem

Before consolidation, the slash command required agents to:
1. Run `objective-fetch-context` and parse JSON output
2. Extract plan references from roadmap YAML
3. Construct `update-objective-node` command with multiple `--node` flags
4. Run the node update and parse results
5. Construct stdin JSON for `objective-post-action-comment`
6. Run the action comment command
7. Parse final results

This was ~150 lines of orchestration with 5+ sequential exec calls, agents parsing JSON and constructing commands between each step.

## The Solution

Consolidate all mechanical operations into a single atomic exec script. See `src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py`:
- Combines fetch-context, update-nodes, and post-action-comment into one call
- Returns rich JSON with everything needed for prose reconciliation
- Agent orchestration reduced to: (1) call consolidated script, (2) reconcile prose, (3) done

## When to Apply This Pattern

Look for these signals in slash commands:
- 5+ sequential `erk exec` calls
- Agents parsing JSON output to construct the next command
- Deterministic work (YAML parsing, JSON construction) with no LLM judgment between steps
- Multiple API operations that should be atomic

## Key Design Decisions

1. **Rich JSON output**: Return comprehensive context so agents don't need follow-up fetches
2. **Single exit point**: All operations in one function ensures atomicity
3. **TypedDict contracts**: Define schemas in `erk-shared` for type-safe consumption
4. **Testable via fakes**: Inject gateways via context, use fake-driven testing for all paths
```

---

#### 6. Workflow Consolidation Pattern Generalization

**Location:** `docs/learned/planning/objective-update-after-land.md`
**Action:** UPDATE
**Source:** [Impl] session-46dd5570-part1, session-8af7820e

**Draft Content:**

Add a "Consolidation Pattern" section to the existing document:

```markdown
## Consolidation Pattern

The objective-update-after-land workflow exemplifies the **sequential command consolidation pattern**:

### Recognition Signals

Apply this pattern when you observe:
- 5+ sequential agent commands in a slash command
- Deterministic work between commands (no LLM judgment needed)
- Agents parsing JSON to construct next command parameters
- Multiple API operations that should succeed or fail atomically

### Before/After Example

**Before (#8069 initial state):**
- 7 steps, ~150 lines
- Agent responsible for: YAML parsing, node ref extraction, JSON construction
- 5+ sequential `erk exec` calls with JSON parsing between each

**After (#8069 consolidated):**
- 3 steps, ~70 lines
- Agent responsible for: calling exec script, prose reconciliation
- Single atomic exec script handles all mechanical work

### Implementation Guide

1. Identify the mechanical operations (no LLM judgment)
2. Create TypedDict for rich JSON output schema
3. Bundle operations into single exec script with atomic behavior
4. Return comprehensive context so agent doesn't need follow-up fetches
5. Leave only work requiring LLM judgment in the slash command
```

---

### LOW Priority

#### 7. Pre-existing Lint Fix Guidance

**Location:** `docs/learned/ci/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] session-46dd5570-part3

**Draft Content:**

```markdown
## Fix Pre-existing Issues Proactively

**When:** Running `make all-ci` or `make lint` and encountering failures in files you didn't modify

**Action:** Fix the pre-existing issues rather than letting them block your submission. Common scenarios:
- Import sorting issues (I001)
- Line too long (E501)
- Missing trailing newline

**Rationale:** Be a good citizen. Pre-existing lint issues accumulate if everyone ignores them. Fixing them during your PR improves codebase health without adding to your change scope.

**Note:** If the fix is non-trivial or risky, consider splitting it into a separate commit or mentioning it in your PR description.
```

---

## Contradiction Resolutions

No contradictions found. The existing documentation is consistent with the implementation.

---

## Stale Documentation Cleanup

No stale documentation found. All code references in existing docs were verified successfully.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Time Gateway API Mismatch

**What happened:** Agent called `time.now(tz=timezone.utc)` expecting it to work like `datetime.now(tz=...)`.

**Root cause:** Gateway ABCs intentionally differ from stdlib APIs. The Time gateway only supports `now()` with no parameters.

**Prevention:** Always read the ABC definition in `src/erk/gateway/` before using gateway methods. Do not assume stdlib API parity.

**Recommendation:** TRIPWIRE (documented as item #2 above)

### 2. Optional Discovery Path Edge Case

**What happened:** Added `--plan` flag to `objective-fetch-context` but didn't update PR discovery logic to handle the case where `branch_name` is `None`.

**Root cause:** When shortcuts bypass normal discovery flows, values that would normally be populated may be `None`. Downstream logic assumed these values were always set.

**Prevention:** When adding optional discovery flags, audit ALL downstream code that uses discovered values for None handling.

**Recommendation:** TRIPWIRE (documented as item #1 above)

### 3. Missing Exec Command Checklist Steps

**What happened:** CI failed because (1) exec reference docs were out of date and (2) prettier wasn't run on command files.

**Root cause:** Multi-step process for adding exec commands that's easy to forget.

**Prevention:** Follow the exec command addition checklist: write tests, register, gen-exec-reference-docs, run prettier.

**Recommendation:** TRIPWIRE (documented as item #3 above)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Optional Discovery Flag Edge Cases

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before adding `--flag` parameter to discovery commands that shortcuts normal discovery flow
**Warning:** Audit all downstream logic for None handling. When shortcuts bypass normal discovery, optional values may be None.
**Target doc:** `docs/learned/objectives/tripwires.md`

This is tripwire-worthy because the edge case (plan provided but branch is None) caused an error that required explicit handling. The pattern applies broadly to any command with optional discovery paths. Without this tripwire, agents will add shortcut flags without realizing they've created new None paths in downstream logic.

### 2. Time Gateway API Mismatch

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** Before using gateway methods in exec scripts
**Warning:** Check ABC definition first. Gateway APIs don't match stdlib (e.g., Time.now() has no tz param).
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because agents naturally assume gateway methods have stdlib-compatible signatures. The Time gateway deliberately differs. This pattern applies to all gateway usage, not just Time.

### 3. Exec Command Addition Checklist

**Score:** 4/10 (Cross-cutting +2, Repeated pattern +1, External tool quirk +1)
**Trigger:** After creating new exec script in `src/erk/cli/commands/exec/scripts/`
**Warning:** Complete checklist: (1) register in group.py, (2) write tests, (3) run gen-exec-reference-docs, (4) run prettier on command files
**Target doc:** `docs/learned/cli/tripwires.md`

This is tripwire-worthy because the multi-step process is easy to forget, and forgetting any step blocks CI. The checklist ensures agents don't submit PRs that fail due to missing generated files or formatting.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Pre-existing Lint Cleanup

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)
**Notes:** Not destructive if ignored (CI just fails until fixed), but agents should proactively fix lint issues to be good citizens. Could be promoted to tripwire if this becomes a frequent blocker.

### 2. CI Rate Limit Recognition

**Score:** 2/10 (External tool quirk +1, Non-obvious +1)
**Notes:** Low impact since it's a transient failure. Agents should recognize "Limit reached" messages as rate limits, not code issues. Not worth a tripwire since the fix is just "wait and retry."

---

## Recommendations for Documentation Authors

### Immediate Actions (HIGH Priority)

1. Add three tripwires to respective category docs (objectives, architecture, cli)
2. Create TypedDict schema reference doc with field descriptions
3. Create exec consolidation pattern doc showing before/after comparison

### Follow-Up Actions (MEDIUM Priority)

4. Update objective-update-after-land.md with consolidation pattern section
5. Update ci/tripwires.md with pre-existing lint fix guidance

### Optional Actions (LOW Priority)

6. Consider quick-submit vs pr-submit workflow guidance if agents show confusion (deferred - self-evident from command names)

### Items to Actively SKIP

- Do NOT document internal helpers (`_update_nodes_in_body`, `_update_comment_table`, `_error_json`) - belongs in code
- Do NOT create new high-level objective workflow docs - already comprehensive coverage
- Do NOT document test patterns separately - 400-line test suite is self-documenting
- Do NOT document command registration pattern - standard, appears everywhere
