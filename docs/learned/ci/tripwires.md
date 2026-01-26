---
title: Ci Tripwires
read_when:
  - "working on ci code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from ci/*.md frontmatter -->

# Ci Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before composing conditions across multiple GitHub Actions workflow steps** → Read [GitHub Actions Workflow Patterns](github-actions-workflow-patterns.md) first. Verify each `steps.step_id.outputs.key` reference exists and matches actual step IDs.

**CRITICAL: Before implementing change detection without baseline capture** → Read [erk-impl Change Detection](plan-implement-change-detection.md) first. Read this doc first. Always capture baseline state BEFORE mutation, then compare AFTER.

**CRITICAL: Before interpolating ${{ }} expressions directly into shell command arguments** → Read [GitHub Actions Security Patterns](github-actions-security.md) first. Use environment variables instead. Direct interpolation allows shell injection. Read [GitHub Actions Security Patterns](ci/github-actions-security.md) first.

**CRITICAL: Before running `git reset --hard` in workflows after staging cleanup** → Read [erk-impl Workflow Patterns](plan-implement-workflow-patterns.md) first. Verify all cleanup changes are committed BEFORE reset; staged changes without commit will be silently discarded.

**CRITICAL: Before running prettier on Python files** → Read [Formatter Tools](formatter-tools.md) first. Prettier cannot format Python. Use `ruff format` or `make format` for Python. Prettier only handles Markdown in this project.

**CRITICAL: Before running prettier programmatically on content containing underscore emphasis** → Read [Formatter Tools](formatter-tools.md) first. Prettier converts `__text__` to `**text**` on first pass, then escapes asterisks on second pass. If programmatically applying prettier, run twice to reach stable output.

**CRITICAL: Before using echo with multi-line content to GITHUB_OUTPUT** → Read [GitHub Actions Output Patterns](github-actions-output-patterns.md) first. Multi-line content requires heredoc syntax with EOF delimiter. Simple echo only works for single-line values.

**CRITICAL: Before using fnmatch for gitignore-style glob patterns** → Read [Convention-Based Code Reviews](convention-based-reviews.md) first. Use pathspec library instead. fnmatch doesn't support \*\* recursive globs. Example: pathspec.PathSpec.from_lines('gitignore', patterns)

**CRITICAL: Before using generic variable names in change detection logic** → Read [erk-impl Change Detection](plan-implement-change-detection.md) first. Use explicit names (UNCOMMITTED, NEW_COMMITS) not generic ones (CHANGES).

**CRITICAL: Before using heredoc (<<) syntax in GitHub Actions YAML** → Read [CI Prompt Patterns](prompt-patterns.md) first. Use `erk exec get-embedded-prompt` instead. Heredocs in YAML `run:` blocks have fragile indentation that causes silent failures.
