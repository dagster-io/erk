---
title: Prettier as Markdown Formatting Authority
read_when:
  - "CI fails with prettier formatting violations"
  - "prettier restores content you removed"
  - "deciding whether to fight prettier's formatting decisions"
tripwires:
  - action: "removing content that prettier restores on formatting"
    warning: "When prettier restores content you removed, it signals the content is structurally necessary. Prettier is the formatting authority — do not fight it."
---

# Prettier as Markdown Formatting Authority

## Resolving Prettier CI Failures

When `make fast-ci` fails due to prettier violations, run prettier on the specific file via devrun:

Ask devrun to run: `npx prettier --write <file-path>`

Do NOT attempt to manually fix formatting issues — prettier's output is authoritative.

## The Restoration Signal

When you remove content from a markdown file and prettier restores it during formatting, this is a signal that the content is structurally necessary for correct markdown rendering. This commonly occurs with:

- Closing backticks in multi-level code block templates
- Blank lines between structural elements
- Trailing newlines

In PR #6949, an automated reviewer flagged a "stray closing backtick" in plan-synthesizer.md. Investigation revealed prettier had restored this backtick because it was structurally necessary for the template's nested code block format. The reviewer's complaint was a false positive.

**Rule:** When prettier disagrees with a manual edit or an automated reviewer, prettier is correct.

## Related Documentation

- [Formatting Workflow](formatting-workflow.md) — General formatting patterns
- [CI Iteration](ci-iteration.md) — Running CI commands via devrun
