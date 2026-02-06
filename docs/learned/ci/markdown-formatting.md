---
title: Markdown Formatting in CI Workflows
read_when:
  - "editing markdown files"
  - "handling Prettier CI failures"
  - "implementing documentation changes"
tripwires:
  - action: "editing markdown files in docs/"
    warning: "Run `make prettier` via devrun after markdown edits. Multi-line edits trigger Prettier failures. Never manually format - use the command."
last_audited: "2026-02-05"
audit_result: edited
---

# Markdown Formatting in CI Workflows

Always run `make prettier` via devrun **after** editing markdown files and **before** running CI. Prettier enforces consistent line wrapping, list formatting, heading spacing, and code block fencing. Manual formatting is error-prone and should never be attempted.

## Standard Workflow

| Phase     | Action                        | Tool         |
| --------- | ----------------------------- | ------------ |
| 1. Edit   | Modify markdown content       | Write/Edit   |
| 2. Format | Run `make prettier`           | devrun agent |
| 3. CI     | Run `make fast-ci`            | devrun agent |
| 4. Fix    | Fix test/lint failures if any | Parent agent |
| 5. Commit | Commit all changes            | Bash/git     |

**Key:** Always format (step 2) before CI (step 3). Skipping formatting wastes a CI cycle.

## Anti-Patterns

- **Manual formatting**: Don't count characters and wrap lines manually. Prettier handles complex rules correctly.
- **Skipping formatting**: Running CI without `make prettier` first will likely fail on Prettier check.
- **Editing via Edit tool to fix formatting**: Run `make prettier` instead — it handles all rules at once.

## Related Documentation

- [CI Iteration Pattern](ci-iteration.md) - devrun delegation pattern
- [Plan Implement CI Customization](plan-implement-customization.md) - Post-implementation CI hooks
- [Formatter Tools](formatter-tools.md) - Overview of prettier, ruff, and other formatters
