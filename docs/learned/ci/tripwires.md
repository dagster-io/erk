---
title: Ci Tripwires
read_when:
  - "working on ci code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from ci/*.md frontmatter -->

# Ci Tripwires

Rules triggered by matching actions in code.

**Add branches-ignore for ephemeral branch patterns** → Read [GitHub Actions Workflow Gating Patterns](workflow-gating-patterns.md) first. Use branches-ignore to prevent workflow queuing for ephemeral branches

**CI job timing out in post-job cleanup** → Read [UV Cache Management in CI](uv-cache-management.md) first. check if UV cache pruning is enabled. Use prune-cache: false for ephemeral CI runners.

**Creating or modifying .prettierignore** → Read [Makefile Prettier Ignore Path](makefile-prettier-ignore-path.md) first. The Makefile uses `prettier --ignore-path .gitignore`, NOT `.prettierignore`. Adding rules to .prettierignore has no effect. Modify .gitignore to control what Prettier ignores.

**GitHub Actions cannot interpolate Python constants** → Read [GitHub Actions Label Filtering Reference](github-actions-label-filtering.md) first. label strings must be hardcoded in YAML

**GitHub Actions workflow needs to perform operations like gist creation, or session uploads fail in CI** → Read [GitHub CLI PR Comment Patterns](github-cli-comment-patterns.md) first. GitHub Actions GITHUB_TOKEN has restricted scope by default. Check token capabilities or use personal access token (PAT) for elevated permissions like gist creation.

**Include cache keys for downloaded binaries** → Read [Composite Action Patterns](composite-action-patterns.md) first. NEVER skip cache keys for downloaded binaries — cache saves 10-20s per workflow run.

**Label checks in push event workflows** → Read [GitHub Actions Label Queries](github-actions-label-queries.md) first. Job-level label access via github.event.pull_request.labels is ONLY available in pull_request events, NOT push events. For push events, you must use step-level GitHub API queries with gh cli or REST API.

**Renaming a GitHub label used in CI automation** → Read [CI Label Rename Checklist](label-rename-checklist.md) first. Labels are referenced in multiple places: (1) Job-level if: conditions in all workflow files, (2) Step name descriptions and comments, (3) Documentation examples showing the label check. Missing any location will cause CI behavior to diverge from intent. Use the CI Label Rename Checklist to ensure comprehensive updates.

**Use direct GCS download for Claude Code installation** → Read [Composite Action Patterns](composite-action-patterns.md) first. NEVER use the curl | bash install script for Claude Code in CI — it hangs unpredictably. Use direct GCS download via setup-claude-code action.

**Use erk-remote-setup for consolidated secret validation** → Read [Composite Action Patterns](composite-action-patterns.md) first. NEVER duplicate secret validation across workflows — use erk-remote-setup's consolidated validation.

**Using escape sequences like `\n` in GitHub Actions workflows** → Read [GitHub CLI PR Comment Patterns](github-cli-comment-patterns.md) first. Use `printf "%b"` instead of `echo -e` for reliable escape sequence handling. GitHub Actions uses dash/sh (POSIX standard), not bash, so `echo -e` behavior differs from local development.

**Writing GitHub Actions workflow steps that pass large content to `gh` CLI commands (e.g., `gh pr comment --body "$VAR"`)** → Read [GitHub CLI PR Comment Patterns](github-cli-comment-patterns.md) first. Use `--body-file` or other file-based input to avoid Linux ARG_MAX limit (~2MB on command-line arguments). Large CI outputs like rebase logs can exceed this limit.

**adding a new CI job that invokes Claude without checking CLAUDE_ENABLED** → Read [Claude Kill Switch](claude-kill-switch.md) first. All Claude CI jobs must check vars.CLAUDE_ENABLED != 'false' before invoking Claude. See claude-kill-switch.md.

**adding a new format-sensitive CI job without including fix-formatting in its needs list** → Read [CI Job Ordering Strategy](job-ordering-strategy.md) first. Format-sensitive jobs (format, docs-check) must depend on both check-submission and fix-formatting. Test jobs (lint, ty, unit-tests, integration-tests, erk-mcp-tests) run speculatively with only check-submission.

**adding code review execution to ci.yml** → Read [CI Job Ordering Strategy](job-ordering-strategy.md) first. Keep shipped review behavior in code-reviews.yml. Repo-local ci.yml should only own formatting, validation, and CI summaries.

**adding new Claude-dependent exec scripts to workflows** → Read [Exec Script Environment Requirements](exec-script-environment-requirements.md) first. Check workflow environment: ANTHROPIC_API_KEY, GH_TOKEN, CLAUDE_CODE_OAUTH_TOKEN

**adding or modifying exec scripts that use require_prompt_executor()** → Read [Exec Script Environment Requirements](exec-script-environment-requirements.md) first. Ensure workflow step has ANTHROPIC_API_KEY in environment. See exec-script-environment-requirements.md

**asking devrun agent to fix errors** → Read [CI Iteration Pattern with devrun Agent](ci-iteration.md) first. devrun is READ-ONLY. Never prompt with 'fix errors' or 'make tests pass'. Use pattern: 'Run command and report results', then parent agent fixes based on output.

**attempting to use prettier on Python files** → Read [Prettier Formatting for Claude Commands](claude-commands-prettier.md) first. Prettier only formats markdown in erk. Python uses ruff format. See formatter-tools.md for the complete matrix.

**calling create_commit_status() immediately after git push** → Read [GitHub Commit Indexing Timing](github-commit-indexing-timing.md) first. GitHub's commit indexing has a race condition. Commits may not be immediately available for status updates after push. Use execute_gh_command_with_retry() wrapper, not direct subprocess calls.

**changing the ci-summarize job `needs` array** → Read [CI Failure Summarization](ci-failure-summarization.md) first. The `needs` array must reference actual job names in ci.yml. Broken references silently skip the job. Verify every name exists.

**committing .erk/impl-context/ without git add -f** → Read [CI Gitignored Directory Commit Patterns](gitignored-directory-commit-patterns.md) first. The directory is gitignored. Use git add -f .erk/impl-context to force-add it. Without -f, git silently skips the directory.

**composing conditions across multiple GitHub Actions workflow steps** → Read [GitHub Actions Workflow Patterns](github-actions-workflow-patterns.md) first. Verify each `steps.step_id.outputs.key` reference exists and matches actual step IDs.

**counting SKIPPED checks in the total** → Read [Check State Classification](check-state-classification.md) first. SKIPPED checks must be excluded from BOTH passing and total counts. They are subtracted from total_count at return time in parse_aggregated_check_counts().

**creating .claude/ markdown commands without formatting** → Read [Prettier Formatting for Claude Commands](claude-commands-prettier.md) first. Run 'make prettier' via devrun after editing markdown. CI will either push an auto-fix commit or fail on unformatted markdown, so don't rely on CI to clean it up.

**creating a new review without checking taxonomy** → Read [Review Types Taxonomy](review-types-taxonomy.md) first. Consult this taxonomy first. Creating overlapping reviews wastes CI resources and confuses PR status checks.

**creating a new review without checking the review types taxonomy** → Read [Automated Review System](automated-review-system.md) first. Consult review-types-taxonomy.md first. Creating overlapping reviews wastes CI resources and confuses PR status checks.

**creating or modifying a reusable GitHub Actions workflow (workflow_call) that depends on ERK_PLAN_BACKEND or other env vars** → Read [GitHub Actions Workflow Patterns](github-actions-workflow-patterns.md) first. Reusable workflow input forwarding: GitHub Actions reusable workflows (via workflow_call) do NOT inherit environment variables from the caller workflow. Declare ERK_PLAN_BACKEND (and any other required env vars) as explicit inputs in the reusable workflow, and pass them explicitly from the caller workflow. Ambient env vars are NOT forwarded automatically.

**creating workflows that invoke Claude without specifying model** → Read [Workflow Model Policy](workflow-model-policy.md) first. All workflows MUST default to claude-opus-4-6. See workflow-model-policy.md for the standardization rationale.

**editing markdown files in docs/** → Read [Markdown Formatting in CI Workflows](markdown-formatting.md) first. Run `make prettier` via devrun after markdown edits. Multi-line edits trigger Prettier failures. Never manually format - use the command.

**implementing change detection without baseline capture** → Read [erk-impl Change Detection](plan-implement-change-detection.md) first. Read this doc first. Always capture baseline state BEFORE mutation, then compare AFTER.

**interpolating ${{ }} expressions directly into shell command arguments** → Read [GitHub Actions Security Patterns](github-actions-security.md) first. Use environment variables instead. Direct interpolation allows shell injection. Read [GitHub Actions Security Patterns](ci/github-actions-security.md) first.

**investigating a bot complaint about formatting** → Read [Prettier Formatting for Claude Commands](claude-commands-prettier.md) first. Prettier is the formatting authority for markdown/YAML/JSON files. If prettier --check passes locally, dismiss the bot complaint. See docs/learned/pr-operations/automated-review-handling.md.

**matching check names from summaries to GitHub check runs** → Read [CI Failure Summarization](ci-failure-summarization.md) first. GitHub prepends 'ci / ' to check names in statusCheckRollup. Use match_summary_to_check() which strips this prefix.

**parsing ERK-CI-SUMMARY markers without re.DOTALL** → Read [CI Failure Summarization](ci-failure-summarization.md) first. Summary content is multiline. The regex uses re.DOTALL so `.` matches newlines. Without it, multiline summaries won't be captured.

**placing test files outside both tests/ and packages/\*/tests/ directories** → Read [Test Coverage Detection](test-coverage-detection.md) first. The test-coverage-review bot only searches tests/**/ and packages/\*/tests/**/ for corresponding test files. Tests placed elsewhere will not be detected and will cause false 'no tests' flags.

**pushing code without running formatters locally first** → Read [Formatting Workflow Decision Tree](formatting-workflow.md) first. Format-then-commit: run ruff format (Python) and prettier (Markdown) locally before pushing. CI may auto-fix same-repo PRs, but that causes a restart and does not help on master pushes or fork PRs.

**reading statusCheckRollup results immediately after push** → Read [CI Iteration Pattern with devrun Agent](ci-iteration.md) first. After push, results show completed runs only, not in-progress. Wait for new check suite to appear before reading CI status.

**referencing \_enable_secret(), \_disable_secret(), or \_display_auth_status() functions** → Read [GitHub Actions API Key Management](dual-secret-auth-model.md) first. These private functions do not exist. The logic is inline within gh_actions_api_key() in src/erk/cli/commands/admin.py.

**resolving git rebase modify/delete conflicts using merge-style terminology** → Read [erk-impl Workflow Patterns](plan-implement-workflow-patterns.md) first. In rebase, 'them' = upstream (opposite to merge). For modify/delete conflicts where the file was deleted upstream, use `git rm <file>` on the conflicted staged files, then `git rebase --continue`. Do not use `git checkout --theirs` which has inverted semantics during rebase.

**running `git reset --hard` in workflows after staging cleanup** → Read [erk-impl Workflow Patterns](plan-implement-workflow-patterns.md) first. Verify all cleanup changes are committed BEFORE reset; staged changes without commit will be silently discarded.

**running only prettier after editing Python files** → Read [Formatting Workflow Decision Tree](formatting-workflow.md) first. Prettier silently skips Python files. Always use 'make format' for .py files.

**running prettier on Python files** → Read [Formatter Tools](formatter-tools.md) first. Prettier cannot format Python. Use `ruff format` or `make format` for Python. Prettier only handles Markdown in this project.

**running prettier programmatically on content containing underscore emphasis** → Read [Formatter Tools](formatter-tools.md) first. Prettier converts `__text__` to `**text**` on first pass, then escapes asterisks on second pass. If programmatically applying prettier, run twice to reach stable output.

**treating NEUTRAL the same as SKIPPED** → Read [Check State Classification](check-state-classification.md) first. NEUTRAL counts as PASSING (it's in PASSING_CHECK_RUN_STATES). Do not confuse with SKIPPED. NEUTRAL checks are real checks that completed successfully with no opinion.

**using Edit tool on Python files** → Read [Edit Tool Formatting Behavior](edit-tool-formatting.md) first. Edit tool preserves exact indentation without auto-formatting. Always run 'make format' after editing Python code.

**using branches-ignore for planned/\* branches** → Read [GitHub Actions Workflow Gating Patterns](workflow-gating-patterns.md) first. planned/ branches contain both metadata AND code. Use paths-ignore instead to skip CI only when commits touch exclusively metadata paths (.erk/impl-context/**, .worker-impl/**).

**using echo with multi-line content to GITHUB_OUTPUT** → Read [GitHub Actions Output Patterns](github-actions-output-patterns.md) first. Multi-line content requires heredoc syntax with EOF delimiter. Simple echo only works for single-line values.

**using fnmatch for gitignore-style glob patterns** → Read [Convention-Based Code Reviews](convention-based-reviews.md) first. Use pathspec library instead. fnmatch doesn't support \*\* recursive globs. Example: pathspec.PathSpec.from_lines('gitignore', patterns)

**using generic variable names in change detection logic** → Read [erk-impl Change Detection](plan-implement-change-detection.md) first. Use explicit names (UNCOMMITTED, NEW_COMMITS) not generic ones (CHANGES).

**using heredoc (<<) syntax in GitHub Actions YAML** → Read [CI Prompt Patterns](prompt-patterns.md) first. Use `erk exec get-embedded-prompt` instead. Heredocs in YAML `run:` blocks have fragile indentation that causes silent failures.

**using label-based gating** → Read [GitHub Actions Label Filtering Reference](github-actions-label-filtering.md) first. Always use negation (!contains) for safe defaults on push events without PR context

**using this pattern** → Read [Workflow Naming Conventions](workflow-naming-conventions.md) first. The CLI command name MUST match the workflow filename (without .yml)

**using this pattern** → Read [Workflow Naming Conventions](workflow-naming-conventions.md) first. The workflow's name: field MUST match the CLI command name

**using this pattern** → Read [Workflow Naming Conventions](workflow-naming-conventions.md) first. Update WORKFLOW_COMMAND_MAP when adding launchable workflows
