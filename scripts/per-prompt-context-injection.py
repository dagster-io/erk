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
print("📌 dignified-python: If not loaded, load now. Always abide by its rules.")
