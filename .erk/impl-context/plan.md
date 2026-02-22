# Plan: Add validate_worktree_name() Backpressure Gate

**Part of Objective #7823, Node 3.1**

## Context

Objective #7823 ("Apply Agent Back Pressure Gates Across Erk") adds validation gates that prevent agents from unknowingly providing names that would be silently transformed. Phase 2 (PR #7845) established the pattern with `validate_plan_title()` returning `ValidPlanTitle | InvalidPlanTitle`.

Node 3.1 adds the same pattern for worktree names: a `validate_worktree_name()` function that checks whether a name would survive `sanitize_worktree_name()` without significant transformation. This is an agent-facing gate — human-facing paths continue to silently sanitize.

## Implementation

### 1. Add discriminated union types to naming.py

**File:** `packages/erk-shared/src/erk_shared/naming.py`

Add after the existing `InvalidPlanTitle` / `validate_plan_title` block (~line 191), before `ValidObjectiveSlug`:

```python
# Worktree name constraints
_WORKTREE_NAME_MAX_LENGTH = 31


@dataclass(frozen=True)
class ValidWorktreeName:
    """Validation success for a worktree name."""
    name: str


@dataclass(frozen=True)
class InvalidWorktreeName:
    """Validation failure for a worktree name."""
    raw_name: str
    reason: str
    diagnostics: list[str]  # Specific issues found

    @property
    def error_type(self) -> str:
        return "invalid-worktree-name"

    def format_message(self) -> str:
        """Full error message with rules and diagnostics for agent self-correction.

        Uses method (not property) because it builds a multi-line string.
        """
        diag_lines = "\n".join(f"    - {d}" for d in self.diagnostics)
        return (
            f"Invalid worktree name: {self.reason}\n"
            f"  Actual value: {self.raw_name!r}\n"
            f"  Diagnostics:\n{diag_lines}\n"
            f"  Rules:\n"
            f"    - Lowercase letters, digits, and hyphens only [a-z0-9-]\n"
            f"    - No underscores (use hyphens)\n"
            f"    - No consecutive hyphens\n"
            f"    - No leading/trailing hyphens\n"
            f"    - Maximum {_WORKTREE_NAME_MAX_LENGTH} characters\n"
            f"  Valid examples: add-auth-feature, fix-bug-123\n"
            f"  Invalid examples: Add_Auth, my__feature, --name"
        )
```

Key design decisions:
- `format_message()` as **method** (not property) per O(1 property constraint and PR #7850 guidance)
- `diagnostics: list[str]` — identifies *which specific* constraints failed, enabling agent self-correction
- Follows `ValidPlanTitle`/`InvalidPlanTitle` pattern exactly

### 2. Add _diagnose_worktree_name() helper

Add a private helper that identifies all constraint violations:

```python
def _diagnose_worktree_name(name: str) -> list[str]:
    """Identify specific validation failures in a worktree name."""
    issues: list[str] = []
    if name != name.lower():
        issues.append("Contains uppercase letters (must be lowercase)")
    if "_" in name:
        issues.append("Contains underscores (use hyphens instead)")
    if re.search(r"[^a-z0-9-]", name):
        # Find the actual bad characters
        bad_chars = sorted(set(re.findall(r"[^a-z0-9-]", name)))
        issues.append(f"Contains invalid characters: {bad_chars}")
    if "--" in name:
        issues.append("Contains consecutive hyphens")
    if name.startswith("-") or name.endswith("-"):
        issues.append("Has leading or trailing hyphens")
    if len(name) > _WORKTREE_NAME_MAX_LENGTH:
        issues.append(f"Too long ({len(name)} characters, maximum {_WORKTREE_NAME_MAX_LENGTH})")
    return issues
```

### 3. Add validate_worktree_name() function

```python
def validate_worktree_name(name: str) -> ValidWorktreeName | InvalidWorktreeName:
    """Validate a worktree name against sanitization rules.

    Agent-facing validation gate. Accepts names that are already clean
    (would pass through sanitize_worktree_name() unchanged). Rejects names
    that would be silently transformed.

    Names with timestamp suffixes (-MM-DD-HHMM) are treated as idempotent
    and pass validation (they've already been sanitized).
    """
    stripped = name.strip()

    if not stripped:
        return InvalidWorktreeName(
            raw_name=name, reason="Empty or whitespace-only", diagnostics=["Name is empty"]
        )

    # Timestamp-suffixed names are idempotent — already sanitized
    if has_timestamp_suffix(stripped):
        return ValidWorktreeName(name=stripped)

    # Check if sanitization would change the name
    sanitized = sanitize_worktree_name(stripped)
    if sanitized == stripped:
        return ValidWorktreeName(name=stripped)

    # Name would be transformed — diagnose why
    diagnostics = _diagnose_worktree_name(stripped)
    if not diagnostics:
        diagnostics = [f"Would be transformed to: {sanitized!r}"]

    return InvalidWorktreeName(
        raw_name=name,
        reason="Name would be silently transformed by sanitization",
        diagnostics=diagnostics,
    )
```

Key insight: Rather than reimplementing all the sanitization rules, we run the name through `sanitize_worktree_name()` and check if `sanitized == stripped`. If they differ, the diagnostics helper tells the agent *why*.

### 4. Add tests

**File:** `tests/core/utils/test_naming.py`

Add after the existing `test_validate_plan_title_*` tests (~line 776):

**Valid worktree names (parametrized):**
- `"add-auth-feature"` — clean lowercase with hyphens
- `"fix-bug-123"` — alphanumeric with hyphens
- `"a" * 31` — at max length
- `"work"` — minimal valid name
- `"my-feature-01-15-1430"` — timestamp-suffixed (idempotent)

**Invalid worktree names (parametrized with reason_fragment):**
- `""` → "empty"
- `"Add_Auth"` → "uppercase" or "underscore"
- `"my__feature"` → "underscore"
- `"FOO-BAR"` → "uppercase"
- `"@@weird"` → "invalid characters"
- `"--name"` → "leading"
- `"name--bad"` → "consecutive hyphens"
- `"a" * 35` → "Too long"

**Structural tests:**
- `test_validate_worktree_name_error_type` — checks `error_type == "invalid-worktree-name"`
- `test_validate_worktree_name_format_message_includes_rules` — checks format_message() contains rules, examples, diagnostics
- `test_validate_worktree_name_preserves_original_in_error` — checks `raw_name` preserves original input
- `test_validate_worktree_name_diagnostics_are_specific` — checks diagnostics list is non-empty and specific

## Files Modified

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/naming.py` | Add `ValidWorktreeName`, `InvalidWorktreeName`, `_diagnose_worktree_name()`, `validate_worktree_name()` |
| `tests/core/utils/test_naming.py` | Add test coverage for worktree name validation |

## Verification

1. Run worktree name validation tests: `pytest tests/core/utils/test_naming.py -k worktree_name`
2. Run full naming tests: `pytest tests/core/utils/test_naming.py`
3. Type check: `ty check packages/erk-shared/src/erk_shared/naming.py`
4. Lint: `ruff check packages/erk-shared/src/erk_shared/naming.py`
