# Documentation Plan: Add slug validation gate to objective creation with agent backpressure

## Context

This plan covers documentation work for PR #7806, which introduced a significant architectural pattern: validation gates for agent-produced output. The core insight is that when agents generate values (like objective slugs), silent sanitization masks agent mistakes and prevents learning. Instead, validation gates provide hard programmatic checks with actionable error messages, enabling agents to self-correct.

The implementation replaced `sanitize_objective_slug()` (which silently transformed any input) with `validate_objective_slug()` returning `ValidObjectiveSlug | InvalidObjectiveSlug`. This discriminated union pattern, combined with detailed error messages containing the pattern, actual value, and examples, creates a feedback loop that teaches agents correct formats. The pattern generalizes beyond slug validation to ANY agent-facing boundary (type checkers, linters, test suites, schema validators).

Documentation matters here because the pattern documentation (`agent-backpressure-gates.md`) was created during implementation but lacks tripwires pointing to it, lacks concrete code examples, and several supporting patterns (gateway parameter threading, agent-facing CLI options) weren't captured. Additionally, the PR review process identified an important anti-pattern (None-as-success) that was fixed but needs to be discoverable for future implementations.

## Raw Materials

PR #7806: https://github.com/dagster-io/erk/pull/7806

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 6     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score 2-3)| 2     |

## Documentation Items

### HIGH Priority

#### 1. Validation gate tripwire

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #7806]

**Draft Content:**

```markdown
## Validation Gates vs Sanitization

**Trigger:** Before implementing input transformation at agent boundaries (e.g., `sanitize_*()` functions for agent-generated data)

**Warning:** Consider a validation gate instead. Sanitization masks agent mistakes and prevents learning. Validation gates give agents clear rules and immediate feedback when they fail.

**Details:** See `validate_objective_slug()` in `naming.py` for the canonical example. For the full pattern, see `docs/learned/architecture/agent-backpressure-gates.md`.
```

---

#### 2. Validation placement in issue creation tripwire

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #7806]

**Draft Content:**

```markdown
## Validation Gate Placement in Issue Creation

**Trigger:** Before adding validation to issue creation workflows

**Warning:** Place gates BEFORE the issue is created, not after. Validate -> early return on failure -> proceed on success. This prevents orphaned issues from validation failures.

**Details:** See `create_objective_issue()` in `plan_issues.py` for validation gate wiring that short-circuits before any GitHub API calls.
```

---

#### 3. Gateway optional parameter threading pattern

**Location:** `docs/learned/architecture/gateway-abc-implementation.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Optional Parameter Threading

When extending gateway metadata functions with new optional fields:

1. Add keyword-only parameter with None default: `def func(*, slug: str | None = None)`
2. Conditionally include in data dict: `if slug is not None: data["slug"] = slug`
3. Add schema validation for optional field
4. Maintains backward compatibility (callers not passing the field continue working)

**Reference:** See `create_objective_header_block()` in `metadata/core.py` for example of threading an optional `slug` parameter through the gateway layer.
```

---

### MEDIUM Priority

#### 4. Discriminated union positive example

**Location:** `docs/learned/architecture/discriminated-union-error-handling.md`
**Action:** UPDATE
**Source:** [Impl], [PR #7806]

**Draft Content:**

```markdown
## Positive Example: ValidObjectiveSlug | InvalidObjectiveSlug

The slug validation gate demonstrates the correct pattern:

- **Explicit success type:** `ValidObjectiveSlug` with `value: str` field
- **Explicit error type:** `InvalidObjectiveSlug` with `actual: str` and `message` property
- **isinstance() dispatch:** Caller checks type and handles each case explicitly

This complements the anti-pattern section added in commit 64f6b0e. The pair demonstrates both what NOT to do (`ErrorType | None` where None = success) and what TO do (explicit named types for both outcomes).

**Reference:** See `validate_objective_slug()` in `naming.py` for implementation.
```

---

#### 5. Actionable error message reference implementation

**Location:** `docs/learned/architecture/agent-backpressure-gates.md`
**Action:** UPDATE
**Source:** [Impl], [PR #7806]

**Draft Content:**

```markdown
## Reference Implementation

`InvalidObjectiveSlug.message` serves as the gold standard for gate error messages:

**Required components:**
1. Error type identification (what kind of failure)
2. Actual value received (what the agent produced)
3. Expected pattern or rules (what was expected)
4. Valid examples (concrete guidance for self-correction)
5. Invalid examples (common mistakes to avoid)

This structure enables agent self-correction without human intervention.

**Reference:** See `InvalidObjectiveSlug.message` property in `naming.py` for the canonical implementation.
```

---

#### 6. Agent-facing CLI option pattern

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Agent-Facing CLI Options

**Trigger:** Before adding a CLI option that agents (not humans) will populate

**Warning:** Agent-facing options have different requirements than user-facing options:
- Optional flag populated from context (skills/commands provide the value)
- Validation failures return non-zero exit with descriptive message
- JSON output format for machine readability
- No interactive prompts (agents cannot respond to prompts)

**When to use:**
- Agent-facing: Value comes from skill context, agent produces it programmatically
- User-facing: Value comes from interactive prompt or user's command line

**Reference:** See `--slug` option on `objective-save-to-issue` in `objective_save_to_issue.py` for an agent-facing option example.
```

---

## Contradiction Resolutions

**No contradictions found.**

All existing documentation provides complementary guidance. The PR composes existing patterns (discriminated unions, two-phase validation, exec scripts) rather than conflicting with them.

## Stale Documentation Cleanup

**No stale documentation detected.**

All reviewed documentation is current with verified code references:
- discriminated-union-error-handling.md: All code references verified
- validation-patterns.md: All code references verified
- objective-create-workflow.md: All code references verified

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Counterintuitive None-as-success return type

**What happened:** Original implementation returned `InvalidObjectiveSlug | None` where None meant success.

**Root cause:** Treating `None` as "no error" when it typically signals absence/failure in Python conventions.

**Prevention:** Always use `SuccessType | ErrorType` discriminated union for validation. None should mean "absence/missing", not "success".

**Recommendation:** TRIPWIRE (already addressed in discriminated-union-error-handling.md via commit 64f6b0e)

### 2. Documentation drift from inline duplication

**What happened:** Documentation duplicated regex pattern `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` inline.

**Root cause:** Natural inclination to show the actual value in documentation for clarity.

**Prevention:** Use source pointers: "checks against `_OBJECTIVE_SLUG_PATTERN` (defined in `naming.py`)" instead of inline duplication.

**Recommendation:** ADD_TO_DOC (addressed in agent-backpressure-gates.md fix commit 64f6b0e)

### 3. Incomplete temporal framing for removed code

**What happened:** Documentation referenced "sanitize_objective_slug() accepts..." in present tense for a removed function.

**Root cause:** Documenting "before/after" migration without clarifying temporal context.

**Prevention:** Use explicit past-tense framing: "The previous implementation (now removed)..."

**Recommendation:** CONTEXT_ONLY (low severity, addressed in fix commit)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Validation gate vs sanitization pattern

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1, External tool quirk +1)
**Trigger:** Before implementing input transformation at agent boundaries (e.g., `sanitize_*()` functions for agent-generated data)
**Warning:** Consider a validation gate instead. Sanitization masks agent mistakes and prevents learning. Validation gates give agents clear rules and immediate feedback when they fail. See docs/learned/architecture/agent-backpressure-gates.md for the pattern.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is the core architectural pattern from the PR. Without this tripwire, future agents may default to sanitization (the common pattern in user-facing code) when they should use validation gates (the correct pattern for agent-facing code). The user correction during planning explicitly broadened this from a narrow slug case to a general reusable pattern.

### 2. Validation placement in issue creation

**Score:** 4/10 (Non-obvious +2, Destructive potential +2)
**Trigger:** Before adding validation to issue creation workflows
**Warning:** Place gates BEFORE the issue is created, not after. Validate -> early return on failure -> proceed on success. This prevents orphaned issues from validation failures.
**Target doc:** `docs/learned/planning/tripwires.md`

Validation that runs after issue creation can leave orphaned GitHub issues when validation fails. The placement in `create_objective_issue()` demonstrates the correct pattern: validate immediately after cheap operations (title extraction) but before expensive operations (GitHub API calls).

### 3. Missing validation gate error message components

**Score:** 4/10 (Non-obvious +2, Silent failure +2)
**Trigger:** Before implementing a validation gate without including pattern/rules in error message
**Warning:** Gate error messages MUST include: (1) the pattern/rules, (2) the actual invalid value, (3) valid examples. Without all three, the agent cannot self-correct. See InvalidObjectiveSlug.message in naming.py for the canonical example.
**Target doc:** `docs/learned/architecture/tripwires.md`

A validation gate without actionable error messages provides rejection but not learning. The agent cannot self-correct if it doesn't know what was wrong or what would be correct. The `InvalidObjectiveSlug.message` property shows all required components.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Agent-facing CLI option pattern

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** This is the first example of an agent-populated option vs user-facing interactive prompt. If the pattern recurs (agents populating more CLI options from context), it may warrant tripwire status. Currently documented as a pattern reference rather than a tripwire because the distinction may be obvious once seen.

### 2. Gateway parameter threading

**Score:** 2/10 (Cross-cutting +2)
**Notes:** Common pattern when extending metadata without breaking backward compatibility. Well-established in existing gateway implementations, so likely doesn't need a tripwire - just a reference example. The pattern is more "how to do it" than "watch out for this footgun."

## Cross-References

Documentation that should reference each other after this plan is implemented:

1. **architecture/tripwires.md** (new tripwires) <-> **architecture/agent-backpressure-gates.md** (pattern doc)
2. **planning/tripwires.md** (validation placement) <-> **architecture/agent-backpressure-gates.md** (pattern doc)
3. **cli/tripwires.md** (agent-facing options) <-> **cli/exec-script-patterns.md** (exec command patterns)
4. **architecture/discriminated-union-error-handling.md** (positive example) <-> **architecture/agent-backpressure-gates.md** (validation gates)
5. **architecture/gateway-abc-implementation.md** (parameter threading) existing 5-place update section

## Implementation Order

For the documentation writer agent:

1. **Start with tripwires** - Add 3 high-priority tripwires to architecture/tripwires.md, planning/tripwires.md, and cli/tripwires.md
2. **Update existing docs first** - Add discriminated union positive example and error message reference implementation
3. **Add gateway pattern** - Document optional parameter threading pattern
4. **Cross-reference** - Add links between tripwires and pattern docs

## Quality Notes

**Documentation Health: EXCELLENT**
- Zero phantom references in existing docs
- Zero contradictions detected
- All PR review issues addressed in commit 64f6b0e

**Pattern Maturity: HIGH**
- Clear architectural vision (gates as general pattern)
- Discriminated unions used correctly (after PR review fix)
- Consistent naming (ValidX | InvalidX)
- Actionable error messages (pattern + value + examples)
