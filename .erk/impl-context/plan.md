# Documentation Plan: Add plan title validation gates for agent-facing save paths

## Context

This implementation added validation gates to all agent-facing plan save paths, ensuring that plans with low-quality or default titles are rejected upstream rather than silently transformed. The core change introduces a `validate_plan_title()` function with discriminated union return types (`ValidPlanTitle | InvalidPlanTitle`) that enforces five validation rules: length constraints (5-100 characters), requiring at least one alphabetic character, meaningful content after sanitization, and rejection of fallback titles like "Untitled Plan" or "Implementation Plan."

Documentation matters here because the implementation establishes several project-wide conventions that future agents must follow: exit code 2 for validation failures (distinguishing "retry with better input" from "escalate to human"), the kebab-case format for `error_type` fields in JSON output, and the pattern of designing error messages that enable agent self-correction. The discriminated union validation pattern and agent backpressure gates are already documented, but the specific application to plan titles and the new tripwires discovered during implementation need to be captured.

A key insight from this implementation is the distinction between agent-facing paths (which use validation gates) and human-facing paths (which use silent transformation). Agents must learn from failures to improve; humans deserve graceful UX that "just works." This principle, already documented in `agent-backpressure-gates.md`, is now concretely applied to plan title handling across both draft-PR and issue-based save pathways.

## Raw Materials

PR #7846

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 10    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Exit Code 2 Convention for Validation Failures

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] + [PR #7846]

**Draft Content:**

```markdown
## Exit Code Convention for Agent-Facing Commands

When implementing validation in agent-facing commands, use stratified exit codes:

- **Exit 0**: Success
- **Exit 1**: System errors (file not found, I/O errors, network failures)
- **Exit 2**: Validation failures (agent-correctable errors)

This distinction allows agents to differentiate between "retry with better input" (exit 2) and "escalate to human" (exit 1). All validation gates in plan-save paths use this convention.

See `src/erk/cli/commands/exec/scripts/` for implementation examples.
```

---

#### 2. error_type Kebab-Case Convention

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] - Session c842fbce discovered pre-existing test bug

**Draft Content:**

```markdown
## error_type Field Format Convention

Always use kebab-case for `error_type` fields in JSON output (not snake_case).

- **Correct**: `"error_type": "invalid-plan-title"`
- **Wrong**: `"error_type": "invalid_plan_title"`

When writing tests that check `error_type` fields, grep existing tests to find the canonical format. This convention was discovered when a test used snake_case but the implementation returned kebab-case, causing silent test failures.

See `tests/core/utils/test_naming.py` for canonical examples.
```

---

#### 3. issue-title-to-filename Breaking Change

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7846]

**Draft Content:**

```markdown
## issue-title-to-filename Validation Behavior

The `issue-title-to-filename` command now validates titles before converting to filenames:

- **Exit code 2** for validation failures (was exit 1 for empty only)
- **JSON error output** on stderr with `error_type` and `agent_guidance` fields
- **Rejects**: empty titles, fallback titles, emoji-only titles, titles that sanitize to nothing

This is a breaking change from previous behavior that only checked for empty strings.

See `src/erk/cli/commands/exec/scripts/issue_title_to_filename.py` for implementation.
```

---

#### 4. agent_guidance Field in JSON Errors

**Location:** `docs/learned/architecture/discriminated-union-error-handling.md`
**Action:** UPDATE
**Source:** [PR #7846]

**Draft Content:**

Add section on agent_guidance field:

```markdown
## Agent Guidance in Error Output

Validation error JSON output includes an `agent_guidance` field designed for agent self-correction:

```json
{
  "success": false,
  "error": "Plan title validation failed: <reason>",
  "error_type": "validation_failed",
  "agent_guidance": "<full message with rules and examples>"
}
```

The `agent_guidance` field contains:
- The actual value that failed validation
- Complete list of validation rules
- Valid and invalid examples

This enables agents to self-correct without human intervention.
```

---

### MEDIUM Priority

#### 5. Plan Title Validation Gates

**Location:** `docs/learned/planning/plan-title-validation-gates.md`
**Action:** CREATE
**Source:** [Plan] + [Impl] + [PR #7846]

**Draft Content:**

```markdown
---
read-when:
  - creating or saving plans via agent-facing commands
  - working with plan title validation
  - adding new plan save pathways
---

# Plan Title Validation Gates

## Overview

All agent-facing plan save paths validate titles before creating branches or issues. This prevents low-quality titles from propagating through the system and ensures agents learn from validation failures.

## Validation Rules

The `validate_plan_title()` function enforces five constraints:

1. **Not empty/whitespace-only**: Title must have non-whitespace content
2. **Length constraints**: 5-100 characters after stripping whitespace
3. **Alphabetic content required**: At least one letter (prevents pure numeric/emoji titles)
4. **No fallback titles**: Rejects "Untitled Plan" and "Implementation Plan" (extractor defaults)
5. **Meaningful after sanitization**: Must not degrade to "plan.md" when sanitized

## Integration Points

Validation occurs in two save pathways:
- Draft-PR saves: See `plan_save.py`
- Issue-based saves: See `plan_save_to_issue.py`

Both return `InvalidPlanTitle` discriminated union on failure with exit code 2.

## Fallback Title Sources

Two extraction functions return different defaults when no title is found:
- `plan_content.extract_title_from_plan()` returns "Untitled Plan"
- `plan_utils.extract_title_from_plan()` returns "Implementation Plan"

Both are rejected because they indicate no real title was provided.

## Agent vs Human Paths

- **Agent-facing paths**: Use `validate_plan_title()` gate - reject and report
- **Human-facing paths**: Use `generate_filename_from_title()` - silently transform

Agents must learn from failures; humans deserve graceful UX.

## Related Documentation

- [Agent Backpressure Gates](../architecture/agent-backpressure-gates.md)
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md)
```

---

#### 6. Agent Self-Correction Error Message Pattern

**Location:** `docs/learned/architecture/agent-error-messages.md`
**Action:** CREATE
**Source:** [PR #7846]

**Draft Content:**

```markdown
---
read-when:
  - designing error messages for agent-facing commands
  - implementing validation that agents must respond to
---

# Agent Self-Correction Error Message Pattern

## Overview

Error messages for agent-facing validation should enable self-correction without human intervention. This requires structured content beyond simple error descriptions.

## Required Elements

1. **error_type**: Machine-readable category (kebab-case)
2. **message property**: Human-readable with full context for self-correction

## Message Format

The message property should include:
- What failed (the specific reason)
- What was provided (the actual value that failed)
- What's required (complete list of validation rules)
- How to fix (valid and invalid examples)

## Implementation Pattern

See `InvalidPlanTitle.message` property in `packages/erk-shared/src/erk_shared/naming.py` for the canonical implementation.

The property constructs a multi-line message including:
- The actual value
- Numbered rules list
- Valid examples
- Invalid examples

This pattern should be reused for all agent-facing validation errors.
```

---

#### 7. Validation Rejection Test Pattern

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Impl] + [PR #7846]

**Draft Content:**

Add section on validation test patterns:

```markdown
## Validation Rejection Test Pattern

When adding validation logic, test comprehensively:

1. **Valid cases**: Confirm successful validation and correct output
2. **Invalid cases**: Confirm rejection with expected error format
3. **JSON format**: Test `error_type` and `agent_guidance` fields
4. **Exit codes**: Verify exit 0 for success, exit 2 for validation failures
5. **Display format**: Test both `--format json` and `--format display` output

Use parametrized tests for comprehensive coverage of edge cases.

**Before writing tests**, grep existing tests to find canonical format:
```bash
Grep(pattern="error_type.*invalid", path="tests/")
```

This prevents format mismatches like snake_case vs kebab-case.
```

---

#### 8. Plan Save Command Validation Gate

**Location:** `.claude/commands/erk/plan-save.md`
**Action:** UPDATE
**Source:** [PR #7846]

**Draft Content:**

Add step showing where title validation occurs:

```markdown
## Validation Gate

Before creating a branch or issue, the plan title is validated:

1. Title extracted from plan markdown (first `# Heading`)
2. `validate_plan_title()` checks constraints
3. On failure: exit 2 with JSON error containing `agent_guidance`
4. On success: proceed with branch/issue creation

If validation fails, retry with a more descriptive plan title.
```

---

### LOW Priority

#### 9. Multi-File Test Discovery Pattern

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Impl] - Session c842fbce

**Draft Content:**

```markdown
## Multi-File Test Discovery

When writing tests for existing features, grep existing tests to find canonical format before writing new tests:

```bash
Grep(pattern="error_type", path="tests/", glob="*.py")
```

This revealed that core tests used kebab-case (`"invalid-plan-title"`) while a CLI test incorrectly used snake_case (`"invalid_plan_title"`). The discrepancy was caught during implementation.
```

---

#### 10. Planning Tripwires - Validation Gates

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7846]

**Draft Content:**

```markdown
## Plan Save Validation Gates

When adding new plan save pathways, all agent-facing paths must validate titles:

- Call `validate_plan_title()` before creating issues/branches/PRs
- Use exit code 2 for validation failures
- Include `agent_guidance` in JSON error output
- Do NOT silently degrade bad titles

See `plan_save.py` and `plan_save_to_issue.py` for implementation pattern.

---

## Agent-Facing vs Human-Facing Paths

Use validation gates (`validate_plan_title()`) for agent-facing paths. Use silent transformation (`generate_filename_from_title()`) only for human-facing paths where graceful UX matters more than learning feedback.
```

---

## Contradiction Resolutions

**No contradictions found.**

All existing documentation is consistent with the new work:
- `agent-backpressure-gates.md` advocates for validation gates over silent transformation
- `discriminated-union-error-handling.md` documents the `ValidThing | InvalidThing` pattern
- The implemented `validate_plan_title()` follows both patterns correctly

---

## Stale Documentation Cleanup

**No stale documentation detected.**

All referenced files verified as existing:
- `packages/erk-shared/src/erk_shared/naming.py` - `validate_plan_title()` found
- `ValidPlanTitle` and `InvalidPlanTitle` classes found
- Integration points in `plan_save.py` and `plan_save_to_issue.py` verified
- All referenced architecture docs exist and are current

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Test Format Mismatch (error_type casing)

**What happened:** Test expected `"invalid_plan_title"` (snake_case) but implementation returned `"invalid-plan-title"` (kebab-case).

**Root cause:** Test written with incorrect casing assumption. No documented convention for `error_type` format.

**Prevention:** Document error_type format convention; use Grep to find existing tests for the same error type before writing new tests.

**Recommendation:** TRIPWIRE - Add to testing/tripwires.md. Score 5: Non-obvious (+2), Silent failure (+2), Cross-cutting (+1).

### 2. Missing Fallback Title Validation

**What happened:** Tests failed with exit code 0 when expecting exit code 2 because `validate_plan_title()` was missing checks for fallback titles.

**Root cause:** Validation function implemented without awareness of the two fallback title sources in the codebase.

**Prevention:** Before implementing plan title validation, grep for existing fallback constants in `plan_content.py` and `plan_utils.py`.

**Recommendation:** ADD_TO_DOC - Include fallback title sources section in plan-title-validation-gates.md.

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Exit Code 2 for Validation Failures

**Score:** 6/10 (Cross-cutting +2, Non-obvious +2, External tool quirk +1, Repeated pattern +1)

**Trigger:** Before implementing validation in agent-facing commands

**Warning:** Use exit code 2 for validation failures (agent can retry with corrected input), exit code 1 for system errors (file not found, I/O errors).

**Target doc:** `docs/learned/cli/tripwires.md`

This is tripwire-worthy because agents encountering validation errors need to know whether to retry or escalate. Exit code 1 means "something is broken, get help." Exit code 2 means "your input was bad, try again." This stratification is project-wide but non-obvious from Python conventions (which typically use exit 1 for all errors).

### 2. error_type Kebab-Case Convention

**Score:** 5/10 (Non-obvious +2, Silent failure +2, Cross-cutting +1)

**Trigger:** Before writing tests that check error_type fields

**Warning:** Always use kebab-case for error_type fields (not snake_case). Grep existing tests to find canonical format.

**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy because the mismatch causes silent test failures. The test asserts against the wrong string, fails, and the agent must debug. Discovered during implementation when a test file used snake_case but the implementation returned kebab-case. Both are reasonable conventions, but erk uses kebab-case.

### 3. issue-title-to-filename Exit Code Change

**Score:** 4/10 (Cross-cutting +2, Non-obvious +2)

**Trigger:** Before calling issue-title-to-filename command

**Warning:** Command now validates titles before converting. Exit code 2 for validation failures, JSON error output on stderr.

**Target doc:** `docs/learned/cli/tripwires.md`

This is tripwire-worthy because it's a breaking change from previous behavior. Scripts or agents that checked for exit code 1 will now see exit code 2 for validation failures. The command's contract has expanded to include full title validation, not just empty-string checking.

---

## Potential Tripwires

Items with score 2-3 that may warrant promotion with additional context:

### 1. Fallback Title Rejection

**Score:** 3/10 (Non-obvious +2, Cross-cutting +1)

**Notes:** Two different modules return different fallback titles - agents should know to avoid them. Currently only affects plan-save paths, but score would increase if more pathways are added that extract titles.

### 2. Plan Title Validation Before Save

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)

**Notes:** Pattern applies to both draft-PR and issue-based save paths. Currently documented in the main plan-title-validation-gates.md doc. Would warrant tripwire promotion if additional save pathways are added (e.g., save to file, save to external system).
