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

**CRITICAL: Before Creating or modifying .prettierignore** → Read [Makefile Prettier Ignore Path](makefile-prettier-ignore-path.md) first. The Makefile uses `prettier --ignore-path .gitignore`, NOT `.prettierignore`. Adding rules to .prettierignore has no effect. Modify .gitignore to control what Prettier ignores.

**CRITICAL: Before GitHub Actions cannot interpolate Python constants** → Read [GitHub Actions Label Filtering Reference](github-actions-label-filtering.md) first. label strings must be hardcoded in YAML

**CRITICAL: Before GitHub Actions workflow needs to perform operations like gist creation, or session uploads fail in CI** → Read [GitHub CLI PR Comment Patterns](github-cli-comment-patterns.md) first. GitHub Actions GITHUB_TOKEN has restricted scope by default. Check token capabilities or use personal access token (PAT) for elevated permissions like gist creation.

**CRITICAL: Before Label checks in push event workflows** → Read [GitHub Actions Label Queries](github-actions-label-queries.md) first. Job-level label access via github.event.pull_request.labels is ONLY available in pull_request events, NOT push events. For push events, you must use step-level GitHub API queries with gh cli or REST API.

**CRITICAL: Before NEVER duplicate secret validation across workflows** → Read [Composite Action Patterns](composite-action-patterns.md) first. use erk-remote-setup's consolidated validation.

**CRITICAL: Before NEVER skip cache keys for downloaded binaries** → Read [Composite Action Patterns](composite-action-patterns.md) first. cache saves 10-20s per workflow run.

**CRITICAL: Before NEVER use the curl | bash install script for Claude Code in CI** → Read [Composite Action Patterns](composite-action-patterns.md) first. it hangs unpredictably. Use direct GCS download via setup-claude-code action.

**CRITICAL: Before Renaming a GitHub label used in CI automation** → Read [CI Label Rename Checklist](label-rename-checklist.md) first. Labels are referenced in multiple places: (1) Job-level if: conditions in all workflow files, (2) Step name descriptions and comments, (3) Documentation examples showing the label check. Missing any location will cause CI behavior to diverge from intent. Use the CI Label Rename Checklist to ensure comprehensive updates.

**CRITICAL: Before Use !contains() pattern for label-based gating** → Read [GitHub Actions Workflow Gating Patterns](workflow-gating-patterns.md) first. Negation is critical — contains() without ! skips all push events

**CRITICAL: Before Using escape sequences like `\n` in GitHub Actions workflows** → Read [GitHub CLI PR Comment Patterns](github-cli-comment-patterns.md) first. Use `printf "%b"` instead of `echo -e` for reliable escape sequence handling. GitHub Actions uses dash/sh (POSIX standard), not bash, so `echo -e` behavior differs from local development.

**CRITICAL: Before Writing GitHub Actions workflow steps that pass large content to `gh` CLI commands (e.g., `gh pr comment --body "$VAR"`)** → Read [GitHub CLI PR Comment Patterns](github-cli-comment-patterns.md) first. Use `--body-file` or other file-based input to avoid Linux ARG_MAX limit (~2MB on command-line arguments). Large CI outputs like rebase logs can exceed this limit.

**CRITICAL: Before adding a test job to autofix's needs list** → Read [Autofix Job Needs](autofix-job-needs.md) first. Test jobs (erkdesk-tests, unit-tests, integration-tests) must NEVER block autofix. Only jobs whose failures can be auto-resolved (format, lint, prettier, docs-check, ty) should be dependencies. Adding test jobs creates a deadlock: tests fail → autofix blocked → format/lint issues never fixed → developer must manually fix both.

**CRITICAL: Before adding new workflows to erk launch** → Read [Workflow Naming Conventions](workflow-naming-conventions.md) first. update WORKFLOW_COMMAND_MAP when adding launchable workflows

**CRITICAL: Before asking devrun agent to fix errors** → Read [CI Iteration Pattern with devrun Agent](ci-iteration.md) first. devrun is READ-ONLY. Never prompt with 'fix errors' or 'make tests pass'. Use pattern: 'Run command and report results', then parent agent fixes based on output.

**CRITICAL: Before attempting to use prettier on Python files** → Read [Prettier Formatting for Claude Commands](claude-commands-prettier.md) first. Prettier only formats markdown in erk. Python uses ruff format. See formatter-tools.md for the complete matrix.

**CRITICAL: Before calling create_commit_status() immediately after git push** → Read [GitHub Commit Indexing Timing](github-commit-indexing-timing.md) first. GitHub's commit indexing has a race condition. Commits may not be immediately available for status updates after push. Use execute_gh_command_with_retry() wrapper, not direct subprocess calls.

**CRITICAL: Before composing conditions across multiple GitHub Actions workflow steps** → Read [GitHub Actions Workflow Patterns](github-actions-workflow-patterns.md) first. Verify each `steps.step_id.outputs.key` reference exists and matches actual step IDs.

**CRITICAL: Before configuring caching for downloaded binaries** → Read [Composite Action Patterns](composite-action-patterns.md) first. NEVER skip cache keys for downloaded binaries - cache saves 10-20s per workflow run.

**CRITICAL: Before creating .claude/ markdown commands without formatting** → Read [Prettier Formatting for Claude Commands](claude-commands-prettier.md) first. Run 'make prettier' via devrun after editing markdown. CI runs prettier-check as a separate job and will fail on unformatted files.

**CRITICAL: Before creating a new review without checking taxonomy** → Read [Review Types Taxonomy](review-types-taxonomy.md) first. Consult this taxonomy first. Creating overlapping reviews wastes CI resources and confuses PR status checks.

**CRITICAL: Before creating new launchable workflows** → Read [Workflow Naming Conventions](workflow-naming-conventions.md) first. the CLI command name MUST match the workflow filename (without .yml)

**CRITICAL: Before editing markdown files in docs/** → Read [Markdown Formatting in CI Workflows](markdown-formatting.md) first. Run `make prettier` via devrun after markdown edits. Multi-line edits trigger Prettier failures. Never manually format - use the command.

**CRITICAL: Before implementing change detection without baseline capture** → Read [erk-impl Change Detection](plan-implement-change-detection.md) first. Read this doc first. Always capture baseline state BEFORE mutation, then compare AFTER.

**CRITICAL: Before installing Claude Code in CI** → Read [Composite Action Patterns](composite-action-patterns.md) first. NEVER use the curl | bash install script - it hangs unpredictably. Use direct GCS download via setup-claude-code action.

**CRITICAL: Before interpolating ${{ }} expressions directly into shell command arguments** → Read [GitHub Actions Security Patterns](github-actions-security.md) first. Use environment variables instead. Direct interpolation allows shell injection. Read [GitHub Actions Security Patterns](ci/github-actions-security.md) first.

**CRITICAL: Before running `git reset --hard` in workflows after staging cleanup** → Read [erk-impl Workflow Patterns](plan-implement-workflow-patterns.md) first. Verify all cleanup changes are committed BEFORE reset; staged changes without commit will be silently discarded.

**CRITICAL: Before running only prettier after editing Python files** → Read [Formatting Workflow Decision Tree](formatting-workflow.md) first. Prettier silently skips Python files. Always use 'make format' for .py files.

**CRITICAL: Before running prettier on Python files** → Read [Formatter Tools](formatter-tools.md) first. Prettier cannot format Python. Use `ruff format` or `make format` for Python. Prettier only handles Markdown in this project.

**CRITICAL: Before running prettier programmatically on content containing underscore emphasis** → Read [Formatter Tools](formatter-tools.md) first. Prettier converts `__text__` to `**text**` on first pass, then escapes asterisks on second pass. If programmatically applying prettier, run twice to reach stable output.

**CRITICAL: Before setting the name field in workflow files** → Read [Workflow Naming Conventions](workflow-naming-conventions.md) first. the workflow's name: field MUST match the CLI command name

**CRITICAL: Before setting up label filtering for push events** → Read [GitHub Actions Label Filtering Reference](github-actions-label-filtering.md) first. always use negation (!contains) for safe defaults on push events without PR context
**CRITICAL: Before skipping cache keys for downloaded binaries** → Read [Composite Action Patterns](composite-action-patterns.md) first. NEVER skip cache keys for downloaded binaries — cache saves 10-20s per workflow run.
**CRITICAL: Before triggering objective reconciliation** → Read [Objective Reconciler Workflow](objective-reconciler-workflow.md) first. The reconcile command launches Claude interactively—it does NOT perform autonomous batch processing. Review actual workflow implementation before assuming sweep behavior.

**CRITICAL: Before using Edit tool on Python files** → Read [Edit Tool Formatting Behavior](edit-tool-formatting.md) first. Edit tool preserves exact indentation without auto-formatting. Always run 'make format' after editing Python code.

**CRITICAL: Before using Python constants in GitHub Actions workflows** → Read [GitHub Actions Label Filtering Reference](github-actions-label-filtering.md) first. GitHub Actions cannot interpolate Python constants - label strings must be hardcoded in YAML
**CRITICAL: Before using contains() for label checks without negation** → Read [GitHub Actions Label Filtering Reference](github-actions-label-filtering.md) first. Always use negation (!contains) for safe defaults on push events without PR context
**CRITICAL: Before using curl | bash install script for Claude Code in CI** → Read [Composite Action Patterns](composite-action-patterns.md) first. NEVER use the curl | bash install script for Claude Code in CI — it hangs unpredictably. Use direct GCS download via setup-claude-code action.
**CRITICAL: Before using echo with multi-line content to GITHUB_OUTPUT** → Read [GitHub Actions Output Patterns](github-actions-output-patterns.md) first. Multi-line content requires heredoc syntax with EOF delimiter. Simple echo only works for single-line values.

**CRITICAL: Before using fnmatch for gitignore-style glob patterns** → Read [Convention-Based Code Reviews](convention-based-reviews.md) first. Use pathspec library instead. fnmatch doesn't support \*\* recursive globs. Example: pathspec.PathSpec.from_lines('gitignore', patterns)

**CRITICAL: Before using generic variable names in change detection logic** → Read [erk-impl Change Detection](plan-implement-change-detection.md) first. Use explicit names (UNCOMMITTED, NEW_COMMITS) not generic ones (CHANGES).

**CRITICAL: Before using heredoc (<<) syntax in GitHub Actions YAML** → Read [CI Prompt Patterns](prompt-patterns.md) first. Use `erk exec get-embedded-prompt` instead. Heredocs in YAML `run:` blocks have fragile indentation that causes silent failures.

**CRITICAL: Before validating secrets in GitHub workflows** → Read [Composite Action Patterns](composite-action-patterns.md) first. NEVER duplicate secret validation across workflows - use erk-remote-setup's consolidated validation.
