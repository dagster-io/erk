#!/usr/bin/env python3
"""Per-prompt context injection hook.

This consolidates three separate reminder hooks into a single script:
- fake-driven-testing reminder
- dignified-python reminder
- devrun agent reminder
"""

print("📌 fake-driven-testing: If not loaded, load now. Always abide by its rules.")
print("🚫 No direct Bash for: pytest/pyright/ruff/prettier/make/gt")
print("✅ Use Task(subagent_type='devrun') instead.")
print(
    """📌 dignified-python: CRITICAL RULES (examples - full skill has more):
❌ NO try/except for control flow (use LBYL - check conditions first)
❌ NO default parameter values (no `foo: bool = False`)
❌ NO mutable/non-frozen dataclasses (always `@dataclass(frozen=True)`)
⚠️ MANDATORY: Load and READ the full dignified-python skill documents.
   These are examples only. You MUST strictly abide by ALL rules in the skill."""
)
print(
    "🧪 AFTER completing Python changes: Verify sufficient test coverage. "
    "Behavior changes ALWAYS need tests."
)
