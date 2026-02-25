# Documentation Plan: Add conditional ErkBot initialization with startup logging and path validation

## Context

This PR introduced conditional initialization for ErkBot within the erkbot Slack application. When the appropriate environment variables are set (ANTHROPIC_API_KEY and ERK_REPO_PATH), the bot initializes an ErkBot agent instance; otherwise, it falls back to a "slack-only" mode with no agent capabilities. This pattern enables graceful degradation for deployments without agent configuration.

The implementation demonstrates several patterns worth documenting: conditional heavy dependency initialization based on environment config, structured startup logging that clearly indicates which mode the application is running in, and path validation using LBYL before object construction. The PR also migrated documentation from line-number-based source pointers to name-based references, which caught an actual drift bug (line 715 had become line 735).

The automated PR review process proved particularly valuable here, catching several issues: bare default parameters in Pydantic config (should use Field()), line numbers in documentation that had already drifted, and conceptual confusion between None and REVIEW_REQUIRED values (both produce no indicator but for semantically different reasons). These review catches inform the tripwire candidates.

## Raw Materials

No gist URL provided for this plan.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 9     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 3     |

## Documentation Items

### HIGH Priority

#### 1. Line Number Drift Anti-Pattern Tripwire

**Location:** `docs/learned/documentation/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8113]

**Draft Content:**

```markdown
## Tripwire Addition (frontmatter)

- action: "citing specific line numbers in documentation references"
  warning: "Use name-based source pointers (function names, constants, variable names with search instructions) instead. Line numbers drift silently with every code edit. See source-pointers.md."
```

The PR caught an actual drift: github-review-decision.md referenced line 715, but the code had moved to line 735. This silent failure makes documentation unreliable. The existing tripwire "using line numbers in source pointers" partially covers this, but agents still cite line numbers in prose explanations. Strengthen the warning.

---

#### 2. Semantic vs Display State Distinction Tripwire

**Location:** `docs/learned/documentation/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8113]

**Draft Content:**

```markdown
## Tripwire Addition (frontmatter)

- action: "documenting multiple values that produce the same visual output"
  warning: "Explicitly explain why they're semantically different, not just what they display. Example: GraphQL null vs enum REVIEW_REQUIRED both show no indicator, but for different reasons (missing data vs awaiting action)."
```

The PR review caught documentation that conflated `None` and `REVIEW_REQUIRED` because both produce no visual indicator. Readers confused "same display" with "same meaning." This is a cross-cutting documentation clarity issue.

---

#### 3. ErkBot Agent Configuration Guide

**Location:** `docs/learned/integrations/erkbot-agent-config.md`
**Action:** CREATE
**Source:** [PR #8113]

**Draft Content:**

```markdown
---
title: ErkBot Agent Configuration
read_when:
  - "configuring erkbot for agent-enabled mode"
  - "troubleshooting erkbot agent initialization"
  - "deploying erkbot with Claude integration"
tripwires:
  - action: "setting only ANTHROPIC_API_KEY without ERK_REPO_PATH"
    warning: "Both fields are required for agent mode. With only one, erkbot falls back to slack-only mode silently."
---

# ErkBot Agent Configuration

ErkBot can run in two modes: agent-enabled (processes tasks via Claude) or slack-only (echoes messages without AI processing).

## Environment Variables

| Variable           | Required | Default                     | Description                        |
| ------------------ | -------- | --------------------------- | ---------------------------------- |
| ANTHROPIC_API_KEY  | For agent| None                        | Anthropic API key for Claude calls |
| ERK_REPO_PATH      | For agent| None                        | Path to erk repository for context |
| ERK_MODEL          | No       | claude-sonnet-4-20250514    | Model ID for agent conversations   |
| ERK_MAX_TURNS      | No       | 10                          | Maximum conversation turns         |

## Mode Selection Logic

See `_run()` function in `packages/erkbot/src/erkbot/cli.py`.

Agent mode activates when:
1. Both `ANTHROPIC_API_KEY` and `ERK_REPO_PATH` are set
2. The path at `ERK_REPO_PATH` exists and is a directory

Otherwise, slack-only mode is used with a warning log.

## Startup Logging

The application logs its mode at startup:
- `mode=agent-enabled model=... repo_path=... max_turns=...` — Agent initialized
- `mode=slack-only` — Running without agent capabilities

## Troubleshooting

**Bot not responding to tasks:**
- Check logs for `mode=slack-only` — agent config may be incomplete
- Verify ERK_REPO_PATH points to a valid directory

**Warning about invalid repo path:**
- Ensure the path exists and is a directory, not a file
- Path validation uses LBYL (`Path.is_dir()`) before construction
```

---

#### 4. Conditional Bot Initialization Pattern

**Location:** `docs/learned/integrations/erkbot-conditional-init.md`
**Action:** CREATE
**Source:** [PR #8113]

**Draft Content:**

```markdown
---
title: Conditional Heavy Dependency Initialization
read_when:
  - "initializing optional features based on environment config"
  - "implementing graceful degradation for missing dependencies"
  - "adding agent or AI integration to existing applications"
tripwires:
  - action: "constructing heavy objects before validating their prerequisites"
    warning: "Validate config fields and paths BEFORE construction. Use LBYL pattern: check required fields present, validate paths exist, then construct."
---

# Conditional Heavy Dependency Initialization

Pattern for conditionally initializing expensive dependencies (API clients, agent instances) based on environment configuration.

## Pattern Structure

See `_run()` in `packages/erkbot/src/erkbot/cli.py` for the canonical implementation.

### 1. Check Required Fields Present

```python
if settings.api_key and settings.resource_path:
    # Proceed to validation
```

### 2. Validate Resources with LBYL

```python
repo_path = Path(settings.resource_path)
if not repo_path.is_dir():
    logger.warning("resource path not a directory, falling back")
    heavy_object = None
else:
    # Proceed to construction
```

### 3. Construct Only When Valid

```python
heavy_object = ExpensiveClient(
    api_key=settings.api_key,
    cwd=repo_path,
    # ... other config
)
```

### 4. Log Mode Clearly

```python
if heavy_object:
    logger.info("mode=feature-enabled key=value ...")
else:
    logger.info("mode=fallback-only")
```

## Key Principles

- **LBYL, not EAFP**: Check `path.is_dir()` before use, don't try/except construction
- **Graceful degradation**: Application continues with reduced capability
- **Clear logging**: Startup logs indicate which mode is active
- **No I/O in constructors**: Validation happens outside, constructor receives validated data

## Related Patterns

- See `docs/learned/architecture/erk-architecture.md` for lightweight `__init__` rule
- See `docs/learned/universal-tripwires.md` for factory method pattern
```

---

### MEDIUM Priority

#### 5. Startup Logging Pattern

**Location:** `docs/learned/integrations/startup-logging-patterns.md`
**Action:** CREATE
**Source:** [PR #8113]

**Draft Content:**

```markdown
---
title: Startup Logging Patterns
read_when:
  - "adding startup logging to an application"
  - "debugging which mode an application started in"
tripwires: []
---

# Startup Logging Patterns

Structured logging pattern for application startup that indicates configuration state.

## Pattern: Mode-Prefixed Key-Value Logs

See startup logging in `packages/erkbot/src/erkbot/cli.py` (search for `logger.info("mode=`).

### Format

```
mode=<mode-name> key1=value1 key2=value2 ...
```

### Example

```python
logger.info(
    f"mode=agent-enabled model={settings.model} "
    f"repo_path={settings.repo_path} max_turns={settings.max_turns}"
)
```

### Benefits

- **Structured**: Key-value format enables log parsing
- **Mode-prefixed**: First field identifies operating mode
- **Context-rich**: Includes all relevant configuration values
- **Debuggable**: Grep for `mode=` to find startup state in logs

## Log Levels

| Situation                     | Level   | Example                           |
| ----------------------------- | ------- | --------------------------------- |
| Normal startup                | INFO    | `mode=agent-enabled ...`          |
| Degraded but functional       | INFO    | `mode=slack-only`                 |
| Config issue with fallback    | WARNING | `repo path not a directory, ...`  |
```

---

#### 6. Pydantic Field() vs Bare Defaults Clarification

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE
**Source:** [PR #8113]

**Draft Content:**

Add section to clarify the Pydantic exception to the "no defaults" rule:

```markdown
## Pydantic Field() Configuration Pattern

The "no default parameter values" rule in dignified-python applies to business logic functions, not Pydantic model definitions. Pydantic `Field()` with defaults is the correct pattern for configuration classes.

### Configuration Classes (Pydantic)

```python
# CORRECT: Field() for configuration
class Settings(BaseSettings):
    max_turns: int = Field(10, alias="MAX_TURNS")
    model: str = Field("claude-sonnet-4", alias="MODEL")
```

### Business Logic Functions

```python
# CORRECT: Keyword-only, no defaults
def process_task(*, max_turns: int, model: str) -> Result:
    ...
```

The distinction: configuration classes define what values CAN be, with sensible defaults. Business logic functions receive those values and shouldn't assume defaults.

See `packages/erkbot/src/erkbot/config.py` for the Settings class implementation.
```

---

#### 7. Source Pointer Migration Example

**Location:** `docs/learned/documentation/source-pointers.md`
**Action:** UPDATE
**Source:** [PR #8113]

**Draft Content:**

Add a section showing the migration pattern from line numbers to names:

```markdown
## Migration Example: Line Numbers to Name-Based References

The github-review-decision.md changes in PR #8113 demonstrate migrating from line-number references to name-based source pointers.

### Before (Fragile)

```markdown
<!-- Source: packages/erk-shared/.../lifecycle.py:67-108 -->
See lines 67-108 in lifecycle.py for display logic.

The wiring connects at Line 573, Line 599, and Line 715.
```

### After (Stable)

```markdown
<!-- Source: packages/erk-shared/.../lifecycle.py, compute_status_indicators -->
See `compute_status_indicators()` in `lifecycle.py` for display logic.

Search for `final_decision_key` assignment and `FINAL_DECISION_FIELD` constant in the wiring code.
```

### Why This Matters

The PR review caught that "Line 715" had already drifted to line 735. Name-based references survive refactoring; line numbers go stale silently.

### Migration Approach

1. Identify the semantic concept being referenced (a function, constant, or variable)
2. Replace line numbers with the symbol name
3. Add search instructions if the symbol isn't unique: "search for X in Y context"
```

---

#### 8. Test Helper Keyword-Only Parameters

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [PR #8113]

**Draft Content:**

Add section on test helper design:

```markdown
## Test Helper Design: Keyword-Only Parameters

Test helper functions that create mock objects should use keyword-only parameters without defaults. This makes test expectations explicit and prevents accidental assumptions.

### Pattern

See `_make_settings_mock()` in `packages/erkbot/tests/test_cli.py`.

```python
def _make_settings_mock(
    *,
    api_key: str | None,
    repo_path: str | None,
    model: str = "test-model",
    max_turns: int = 10,
) -> MagicMock:
    """Create mock Settings with explicit configuration.

    Required fields (api_key, repo_path) have no defaults — tests must
    explicitly set them to None or a value. Optional fields (model, max_turns)
    have sensible defaults.
    """
    ...
```

### Benefits

- **Explicit expectations**: `api_key=None` is clearer than implicit None
- **Prevents copy-paste bugs**: New tests must consider all required fields
- **Documents intent**: Keyword-only syntax (`*,`) signals "think about these"

### When to Apply

- Mock/fixture factories for configuration objects
- Test helpers that construct complex test state
- Any helper where "missing" vs "explicitly None" has different meaning
```

---

### LOW Priority

#### 9. Path Validation Before Construction Example

**Location:** `docs/learned/architecture/erk-architecture.md`
**Action:** UPDATE
**Source:** [PR #8113]

**Draft Content:**

Add bot/agent initialization as an example in the existing lightweight `__init__` discussion:

```markdown
## Path Validation Before Construction

When constructing objects that depend on filesystem paths, validate the path BEFORE calling the constructor. This is an extension of the lightweight `__init__` principle.

### Example: Agent Initialization

See `_run()` in `packages/erkbot/src/erkbot/cli.py`.

```python
# Validate path BEFORE construction
repo_path = Path(settings.repo_path)
if not repo_path.is_dir():
    logger.warning("repo path not valid directory")
    bot = None
else:
    # Constructor receives already-validated path
    bot = AgentBot(cwd=repo_path, ...)
```

### Principles

- **LBYL pattern**: Check `path.exists()` and `path.is_dir()` before use
- **No I/O in constructors**: Constructor should not validate paths
- **Clear failure mode**: Validation failure leads to explicit fallback, not exception
```

---

## Contradiction Resolutions

**None identified.** All existing documentation aligns with the changes in this PR. The lightweight `__init__` pattern and factory method guidance in existing docs are consistent with the conditional bot initialization approach.

## Stale Documentation Cleanup

**None required.** All referenced files in existing documentation were verified to exist. No phantom references detected.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Line Number Drift

**What happened:** Documentation referenced line 715, but code had moved to line 735.
**Root cause:** Line numbers shift with every edit; documentation can't track these changes.
**Prevention:** Use name-based references (function names, constants, variables) that survive refactoring.
**Recommendation:** TRIPWIRE (score 6)

### 2. Semantic vs Display Conflation

**What happened:** Documentation described `None` and `REVIEW_REQUIRED` as "both showing no indicator" without explaining they're semantically different.
**Root cause:** Documentation focused on visual output, not underlying meaning.
**Prevention:** When documenting values with same display, explicitly state why they differ.
**Recommendation:** TRIPWIRE (score 5)

### 3. Bare Default Parameters in Pydantic

**What happened:** Initial code used `max_turns: int = 10` instead of `Field(10, alias="...")`.
**Root cause:** Confusion between Pydantic config patterns and general Python function rules.
**Prevention:** Clarify in conventions that Pydantic Field() is the exception to "no defaults."
**Recommendation:** ADD_TO_DOC

### 4. Implicit Test Helper Parameters

**What happened:** Test helper had default parameters that hid test intentions.
**Root cause:** Copy-paste from other test files without considering explicitness.
**Prevention:** Document that test helpers for config objects should use keyword-only params.
**Recommendation:** ADD_TO_DOC

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Line Number References in Documentation

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before citing specific line numbers in documentation
**Warning:** Use name-based source pointers (function names, constants, variable names with search instructions) instead. Line numbers drift silently with every code edit.
**Target doc:** `docs/learned/documentation/tripwires.md`

This is tripwire-worthy because the failure mode is silent: documentation looks authoritative even when line numbers are wrong. The PR caught a real instance (715 → 735). Every documentation file is vulnerable.

### 2. Same Display, Different Semantics

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** When documenting multiple values that produce the same visual output
**Warning:** Explicitly explain why they're semantically different, not just what they display.
**Target doc:** `docs/learned/documentation/tripwires.md`

This is tripwire-worthy because readers naturally conflate "looks the same" with "means the same." The PR example (None vs REVIEW_REQUIRED) is one instance of a broader pattern that appears in any system with nullable enums or optional fields.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Conditional Heavy Dependency Initialization

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** The pattern (check config → validate paths → construct or fallback) is reusable for other optional integrations, but currently only one example exists. If more integrations follow this pattern, promote to tripwire.

### 2. Pydantic Field() vs Bare Defaults

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** The distinction between config classes and business logic is nuanced. Pydantic-specific, so limited scope. May warrant tripwire if confusion persists.

### 3. Path Validation Before Construction

**Score:** 2/10 (Non-obvious +2)
**Notes:** Extends the existing lightweight `__init__` pattern documented in erk-architecture.md. Not a new concern — the existing tripwire about I/O in constructors covers this. Low priority.

## Automated Review Workflow Validation

This PR demonstrates the automated review infrastructure catching real issues:

**Issues caught before merge:**
- Line number drift (before it caused reader confusion)
- Conceptual clarity gaps (None vs REVIEW_REQUIRED)
- Code style violations (bare defaults)
- Test pattern violations (implicit parameters)

**Metrics:**
- 3 review rounds
- 0 false positives
- 4 categories of issues caught

This validates the automated review approach and informs the tripwire recommendations above.
