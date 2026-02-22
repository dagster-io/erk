# Documentation Plan: Add discriminated union validation gate and enhanced schema guidance for tripwire candidates

## Context

This plan captures learnings from PR #7836, which replaced exception-based validation with discriminated union types for tripwire candidate validation. The implementation introduced a two-phase validation gate pattern: a pre-normalization salvageability check that rejects structurally broken input early, followed by post-normalization validation that catches invalid normalized data. This pattern is significant because it provides a reusable approach for handling agent-produced data with predictable drift patterns.

The PR also enhanced agent guidance with strict schema enforcement documentation, including field naming normalization tables and valid/invalid examples. A key innovation is the `InvalidTripwireCandidates.message` property, which provides structured error messages (reason + schema + rules + valid example + invalid example) that agents can self-correct from, reducing iteration count and agent drift.

Beyond the core implementation, the associated sessions revealed important patterns for objective management: the workflow for adding nodes to objectives requires manual YAML editing followed by validation, and the `update-objective-node` command has non-obvious required flags that cause `missing_ref` errors when omitted. These operational insights are equally valuable for future agents.

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 13 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 4 |
| Potential tripwires (score 2-3) | 3 |

## Documentation Items

### HIGH Priority

#### 1. Validation Gate Pattern (Pre/Post Normalization)

**Location:** `docs/learned/architecture/validation-gates.md`
**Action:** CREATE
**Source:** [Impl], [PR #7836]

**Draft Content:**

```markdown
---
read-when:
  - designing validation for agent-produced data
  - handling predictable agent drift patterns
  - implementing multi-phase validation
tripwire-count: 0
---

# Validation Gate Pattern

Two-phase validation gates provide defense-in-depth for agent-produced data with predictable drift patterns.

## Pattern Overview

The validation gate pattern separates validation into two phases:

1. **Pre-normalization salvageability check**: Reject structurally broken input early (e.g., array roots, missing required keys)
2. **Post-normalization validation**: Validate after normalization has applied field mappings and structural fixes

## When to Use

Use validation gates when:
- Input comes from agents that may produce predictable drift (field name variations, wrapped roots)
- You want to distinguish between salvageable drift and unsalvageable structural errors
- Early rejection improves error messages and reduces wasted processing

## Implementation Pattern

See `src/erk/cli/commands/exec/scripts/normalize_tripwire_candidates.py` for the canonical implementation:
- `check_salvageable()` function implements the pre-gate
- Post-normalization validation gate follows the normalization step

## Discriminated Union Results

Validation gates return discriminated unions, not exceptions:

- `ValidX | InvalidX` return types make control flow explicit
- Callers use `isinstance()` checks instead of `try/except`
- Error messages can include actionable guidance for agent self-correction

See `docs/learned/architecture/discriminated-union-error-handling.md` for the error handling pattern.
```

---

#### 2. Agent Error Message Design

**Location:** `docs/learned/planning/agent-error-messages.md`
**Action:** CREATE
**Source:** [Impl], [PR #7836]

**Draft Content:**

```markdown
---
read-when:
  - designing error messages for agent-facing APIs
  - building validation that agents can self-correct from
  - reducing agent iteration count on errors
tripwire-count: 0
---

# Agent Error Message Design

When building validation gates for agent-produced data, error messages should be actionable enough that agents can self-correct without human intervention.

## Structure

Effective agent error messages include:

1. **Reason**: What specific validation failed
2. **Schema**: The expected structure (TypedDict or similar)
3. **Rules**: Specific constraints that must be satisfied
4. **Valid example**: A complete, correct example
5. **Invalid example**: The problematic input (when helpful)

## Canonical Example

See `InvalidTripwireCandidates.message` property in `packages/erk-shared/src/erk_shared/gateway/github/metadata/tripwire_candidates.py` for the reference implementation.

## Benefits

- Agents can self-correct on first retry
- Reduces iteration count and token usage
- Error messages serve as inline documentation
- Validation becomes a "teaching" mechanism for agent drift

## Anti-patterns

- Generic error messages: "Invalid input"
- Missing schema reference: Agent must guess structure
- No examples: Agent lacks concrete guidance
```

---

#### 3. Update-objective-node Required Flags

**Location:** `docs/learned/objectives/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl]

This is a tripwire candidate with score 6 (Non-obvious +2, Cross-cutting +2, Silent failure until runtime +2).

When calling `erk exec update-objective-node`, agents MUST include either `--plan` or `--pr` flag. The command will fail with `missing_ref` error if both are omitted, even when only updating status. This is not obvious from the command usage and caused errors during implementation.

**Draft Content:**

```markdown
## Update-objective-node Reference Requirement

**Trigger:** Before calling `erk exec update-objective-node`

**Warning:** ALWAYS include either `--plan` or `--pr` flag. The command will fail with `missing_ref` error if both are omitted, even when only updating status. Use `--plan ''` to explicitly clear the plan field if needed.

**Context:** The command enforces that nodes have at least one reference for traceability. This is a validation constraint, not a bug.
```

---

#### 4. Objective Validation After Manual Edit

**Location:** `docs/learned/objectives/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl]

This is a tripwire candidate with score 5 (Non-obvious +2, Destructive potential +2, Repeated pattern +1).

Manual YAML edits to objective issue bodies can break objective metadata. After manually editing objective issue body YAML, agents MUST run `erk objective check <number>` to validate structure before proceeding with updates.

**Draft Content:**

```markdown
## Objective Validation After Manual Edit

**Trigger:** After manually editing objective issue body

**Warning:** ALWAYS run `erk objective check <number>` to validate structure before proceeding with updates. Manual YAML edits can break objective metadata.

**Context:** Objective roadmap YAML has validation rules (node structure, status constraints). Manual edits bypass client-side validation, so explicit server-side check is required.
```

---

### MEDIUM Priority

#### 5. Discriminated Union Validation Gate Section

**Location:** `docs/learned/architecture/discriminated-union-error-handling.md`
**Action:** UPDATE
**Source:** [Impl], [PR #7836]

**Draft Content:**

```markdown
## Validation Gates: Discriminated Unions for Validation Results

Beyond error handling, discriminated unions provide a pattern for validation results themselves.

### Pattern: ValidX | InvalidX

When validation can fail with actionable errors, return a discriminated union:

- `ValidTripwireCandidates` contains the validated data
- `InvalidTripwireCandidates` contains error details with actionable message

Callers use `isinstance()` checks to branch:

```python
result = validate_candidates_data(data)
if isinstance(result, InvalidTripwireCandidates):
    # Handle error with result.message
    return
# Use result.candidates (the validated data)
```

### Benefits Over Exceptions

- Explicit control flow (no hidden exception paths)
- Error messages can include full context (schema, examples)
- Testable without `pytest.raises()`
- Aligns with LBYL principles

### When to Use

Use for validation gates where:
- Errors should be actionable (agent self-correction)
- Control flow should be explicit
- Testing benefits from isinstance checks

See `packages/erk-shared/src/erk_shared/gateway/github/metadata/tripwire_candidates.py` for implementation.
```

---

#### 6. Breaking API Changes Documentation

**Location:** `docs/learned/architecture/discriminated-union-error-handling.md`
**Action:** UPDATE
**Source:** [PR #7836]

**Draft Content:**

```markdown
## Migration: Exception-based to Discriminated Union Validation

When migrating validation functions from exceptions to discriminated unions:

### Signature Changes

- Old: `def validate_x(data: dict) -> list[T]` (raises on error)
- New: `def validate_x(data: Any) -> ValidX | InvalidX`

### Caller Migration

Replace:
```python
try:
    items = validate_x(data)
except ValidationError as e:
    handle_error(e)
```

With:
```python
result = validate_x(data)
if isinstance(result, InvalidX):
    handle_error(result.message)
    return
items = result.items
```

### Example

See `validate_candidates_data()` and `validate_candidates_json()` in tripwire_candidates.py for the canonical example.
```

---

#### 7. LBYL Validation Pattern Example

**Location:** `docs/learned/architecture/lbyl-gateway-pattern.md`
**Action:** UPDATE
**Source:** [PR #7836]

**Draft Content:**

```markdown
## LBYL for Validation Control Flow

The LBYL pattern applies to validation logic, not just gateway operations.

### Pattern

Use `isinstance()` checks instead of `try/except` for validation branches:

```python
# LBYL (correct)
if isinstance(data, dict) and "candidates" in data:
    process(data["candidates"])
else:
    handle_invalid()

# EAFP (avoid in erk)
try:
    process(data["candidates"])
except (KeyError, TypeError):
    handle_invalid()
```

### When Exceptions Are Acceptable

Exceptions remain appropriate for I/O boundaries where failures are exceptional:
- `json.loads()` - malformed JSON is exceptional
- File operations - missing file is exceptional
- Network calls - connection failures are exceptional

But validation logic (checking structure, types, constraints) should use LBYL.

See `src/erk/cli/commands/exec/scripts/store_tripwire_candidates.py` for LBYL validation pattern.
```

---

#### 8. Objective Node Creation Workflow

**Location:** `docs/learned/objectives/node-management.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - adding new nodes to objectives
  - associating PRs with objectives
  - manual objective YAML editing
tripwire-count: 0
---

# Objective Node Management

This doc covers workflows for managing objective nodes, including creation, association, and validation.

## Adding New Nodes

There is no `erk` command for creating nodes. The workflow is:

1. **Manually edit issue body YAML** to add the new node entry
2. **Update via `gh issue edit`** to persist the changes
3. **Validate with `erk objective check <number>`** to ensure structure is correct
4. **Then use `erk exec update-objective-node`** to update the node with references

## Common Errors

- `node_not_found`: Tried to update a node that doesn't exist in the YAML
- `missing_ref`: `update-objective-node` requires `--plan` or `--pr` flag

## Validation Constraints

Nodes with plan references must have status `planning`, `in_progress`, or `done` (not `pending`). This validation constraint is enforced by `erk objective check`.
```

---

#### 9. Objective Matching Strategy

**Location:** `docs/learned/objectives/node-matching-strategy.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - matching PRs to objectives
  - deciding which objective node fits a PR
  - associating work with objectives
tripwire-count: 0
---

# Objective Node Matching Strategy

When associating PRs with objectives, match thematic intent rather than requiring exact description match.

## Heuristic

1. **Identify the PR's intent**: What is the PR trying to accomplish? (cleanup, consolidation, new feature, bug fix)
2. **Map to objective themes**: Which objective node covers that type of work?
3. **Accept thematic matches**: "consolidating exec commands" matches "Clean Up Legacy Infrastructure" even if no node mentions "exec commands" specifically

## Examples

| PR Intent | Objective Theme | Match Rationale |
|-----------|-----------------|-----------------|
| Consolidate plan-header metadata commands | Clean Up Legacy Plan Infrastructure | Consolidation = cleanup |
| Add discriminated union validation | Validation robustness | Pattern improvement = architectural progress |

## Anti-patterns

- Requiring exact textual match between PR title and node description
- Creating new nodes for every PR (nodes should be broader goals)
- Leaving PRs unassociated because no node matches perfectly
```

---

#### 10. Discriminated Union Testing Pattern

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [PR #7836]

**Draft Content:**

```markdown
## Testing Discriminated Union Returns

When testing functions that return discriminated unions (`ValidX | InvalidX`), prefer `isinstance()` checks over `pytest.raises()`.

### Pattern

```python
def test_invalid_input_returns_invalid_type():
    result = validate_something(bad_data)
    assert isinstance(result, InvalidSomething)
    assert "expected error text" in result.message

def test_valid_input_returns_valid_type():
    result = validate_something(good_data)
    assert isinstance(result, ValidSomething)
    assert result.items == expected_items
```

### Benefits

- Consistent with LBYL pattern
- No exception handling needed in tests
- Clear assertion on result type
- Error message content easily verified

### Migration

When migrating tests from exception-based to discriminated union:

Replace:
```python
with pytest.raises(ValidationError, match="error text"):
    validate_something(bad_data)
```

With:
```python
result = validate_something(bad_data)
assert isinstance(result, InvalidSomething)
assert "error text" in result.message
```

See `tests/shared/github/test_tripwire_candidates_metadata.py` for examples.
```

---

### LOW Priority

#### 11. PR-to-Objective Association Workflow

**Location:** `docs/learned/objectives/objective-operations.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## PR-to-Objective Association Workflow

To associate a PR with an objective node:

1. **Ensure node exists**: Check if the target node exists in the objective's roadmap YAML. If not, add it manually (see node-management.md).

2. **Validate structure**: Run `erk objective check <number>` to ensure the objective structure is valid.

3. **Associate the PR**: Run `erk exec update-objective-node <issue> --node <id> --pr '#<PR_NUMBER>' --plan '' --status done`
   - Use `--plan ''` to explicitly clear the plan field if needed
   - Set appropriate status (`planning`, `in_progress`, or `done`)

4. **Validate again**: Run `erk objective check <number>` to confirm the update was valid.
```

---

#### 12. Node Status Validation Rule

**Location:** `docs/learned/objectives/objective-operations.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Node Status Validation Constraints

Nodes with plan references have status constraints:

- **Valid statuses**: `planning`, `in_progress`, `done`
- **Invalid**: `pending` (cannot have a plan reference with pending status)

The rationale: if a node has a plan reference, work has begun, so it cannot be "pending".

### Common Error

```
Validation failure: "Step 3.1 has plan #7834 but status is 'pending'"
```

**Fix**: Update the node's status to `planning` when associating a plan reference.
```

---

#### 13. Parallel Verification Pattern

**Location:** `docs/learned/objectives/objective-operations.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Parallel Verification Pattern

When auditing objective references, launch independent Grep searches in parallel for efficiency:

```python
# Run multiple independent searches simultaneously
Grep(pattern="class GitHubPlanStore", path="src/")
Grep(pattern="extract_leading_issue_number", path="src/")
Grep(pattern="plan_create_review_branch", path=".github/")
```

This pattern reduces total verification time when checking multiple references that don't depend on each other.
```

---

## Contradiction Resolutions

**No contradictions detected.**

All existing documentation is internally consistent:
- `agent-schema-enforcement.md` recommends normalize-then-validate (3-layer defense-in-depth)
- `discriminated-union-error-handling.md` recommends discriminated unions for branching logic
- `lbyl-gateway-pattern.md` recommends checking before operating
- `exec-script-schema-patterns.md` recommends TypedDict for schema + LBYL guards

These patterns are complementary and the new validation gate pattern extends them.

---

## Stale Documentation Cleanup

**No stale documentation detected.**

All code references in relevant docs point to existing files:
- `src/erk/cli/commands/exec/scripts/normalize_tripwire_candidates.py` (EXISTS)
- `src/erk/cli/commands/exec/scripts/store_tripwire_candidates.py` (EXISTS)
- `packages/erk-shared/src/erk_shared/learn/tripwire_promotion.py` (EXISTS)
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/tripwire_candidates.py` (EXISTS)

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Node Update Before Node Creation

**What happened:** Agent tried to update node 3.2 before adding it to the roadmap YAML, receiving `node_not_found` error.
**Root cause:** Assumed `erk exec update-objective-node` would create the node if it didn't exist.
**Prevention:** Before updating a node, verify it exists in the YAML. If not, add node to YAML first, validate, then update.
**Recommendation:** ADD_TO_DOC (node-management.md workflow)

### 2. Objective Validation Failure After Node Update

**What happened:** Updated node's plan reference without updating status field, causing validation failure: "Step 3.1 has plan #7834 but status is 'pending'".
**Root cause:** Did not know that nodes with plan references must have non-pending status.
**Prevention:** After associating a plan with a node, ALWAYS update status to "planning" (or "in_progress"/"done").
**Recommendation:** TRIPWIRE (score 5, documented above)

### 3. Missing Reference on Update-objective-node

**What happened:** Called `erk exec update-objective-node` without `--plan` or `--pr` flag, receiving `missing_ref` error.
**Root cause:** Assumed status-only updates were allowed without reference flags.
**Prevention:** Always include at least one reference flag (`--plan` or `--pr`).
**Recommendation:** TRIPWIRE (score 6, documented above)

### 4. Assumed Command Exists Without Checking

**What happened:** Ran `erk objective associate` which doesn't exist.
**Root cause:** Invented a command name without checking available subcommands.
**Prevention:** Run `erk <group> -h` or `erk exec -h | grep <pattern>` to discover available commands first.
**Recommendation:** TRIPWIRE (score 4, documented below)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Update-objective-node Missing --plan or --pr Flag

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure until runtime +2)
**Trigger:** Before calling `erk exec update-objective-node`
**Warning:** ALWAYS include either `--plan` or `--pr` flag. The command will fail with `missing_ref` error if both are omitted, even when only updating status.
**Target doc:** `docs/learned/objectives/tripwires.md`

This is tripwire-worthy because the command's help text doesn't make it obvious that at least one reference is always required. The error only manifests at runtime, and the requirement is non-obvious from the command signature.

### 2. Objective Validation After Manual YAML Edit

**Score:** 5/10 (Non-obvious +2, Destructive potential +2, Repeated pattern +1)
**Trigger:** After manually editing objective issue body
**Warning:** ALWAYS run `erk objective check <number>` to validate structure before proceeding with updates. Manual YAML edits can break objective metadata.
**Target doc:** `docs/learned/objectives/tripwires.md`

Manual YAML editing bypasses client-side validation, making it easy to introduce structural errors that only surface when the next operation fails. Validation should be habitual after any manual edit.

### 3. Node Has Plan Reference but Pending Status

**Score:** 5/10 (Non-obvious +2, Destructive potential +2, External tool quirk +1)
**Trigger:** When associating a plan reference with an objective node
**Warning:** MUST update status to 'planning' (or 'in_progress'/'done'), not leave as 'pending'. Nodes with plan references must have non-pending status (validation constraint).
**Target doc:** `docs/learned/objectives/tripwires.md`

This constraint makes semantic sense (if a plan exists, work has started), but it's not obvious and causes validation failures that interrupt workflow.

### 4. Premature User Escalation (Assumed Command Doesn't Exist)

**Score:** 4/10 (Non-obvious +2, Repeated pattern +1, Cross-cutting +1)
**Trigger:** Before inventing command names or asking user for clarification
**Warning:** Run `erk <group> -h` or `erk exec -h | grep <pattern>` to discover available commands first. When user says "find it", exhaust search strategies before asking for input.
**Target doc:** `docs/learned/cli/tripwires.md`

The session showed an agent inventing `erk objective associate` without first checking available commands. When the user directed "find it", the agent should have searched more thoroughly rather than asking for clarification.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Search Scope Insufficiency (src/ to Full Repo)

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)
**Notes:** When searching for class/function usage, agents often start with `src/` but need to expand to include `packages/`. This is a common pattern but may not be harmful enough to warrant a tripwire if agents learn quickly from initial search results.

### 2. Terminology Drift in Objective Descriptions

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** Objective node descriptions may reference outdated terminology (e.g., "PLAN_BACKEND constant" when it's now "get_plan_backend() function"). Specific to objectives workflow; not cross-cutting enough for universal tripwire. Consider documenting as pattern in objective reevaluation guide.

### 3. Command Discovery Before Invention

**Score:** 2/10 (Non-obvious +2)
**Notes:** Good pattern (check `--help` before inventing commands) but the harm from getting it wrong is just an error message that immediately redirects. Consider documenting as best practice rather than tripwire.
