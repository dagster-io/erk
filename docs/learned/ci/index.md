<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Ci Documentation

- **[autofix-job-needs.md](autofix-job-needs.md)** — modifying the autofix job's needs list in ci.yml, adding a new CI job that might block autofix, understanding why autofix runs independently of tests
- **[ci-iteration.md](ci-iteration.md)** — running CI commands in workflows, delegating pytest, ty, ruff commands, understanding devrun agent restrictions
- **[claude-code-docker.md](claude-code-docker.md)** — Running Claude Code in GitHub Actions containers, Debugging permission errors in CI Docker containers, Choosing between container and container-less CI approaches
- **[claude-commands-prettier.md](claude-commands-prettier.md)** — Creating slash commands in .claude/commands/, Modifying existing .claude/ markdown files, Getting Prettier formatting errors in CI
- **[claude-kill-switch.md](claude-kill-switch.md)** — modifying CI workflows that invoke Claude, understanding how to emergency-disable Claude in CI, working with the CLAUDE_ENABLED variable
- **[commit-squash-divergence.md](commit-squash-divergence.md)** — encountering 'fetch first' after gt submit, dealing with divergent branches after Graphite operations, understanding expected vs unexpected branch divergence, working with Graphite PR submission workflow
- **[composite-action-patterns.md](composite-action-patterns.md)** — creating reusable GitHub Actions setup steps, using erk-remote-setup composite action, understanding GitHub Actions composite patterns
- **[containerless-ci.md](containerless-ci.md)** — Setting up Claude Code in GitHub Actions without containers, Comparing container vs container-less CI approaches, Choosing between container and container-less CI approaches
- **[convention-based-reviews.md](convention-based-reviews.md)** — adding a new code review to CI, understanding how code reviews work, modifying code review behavior
- **[edit-tool-formatting.md](edit-tool-formatting.md)** — using the Edit tool to modify Python code, encountering formatting issues after edits, CI failing on formatting checks after using Edit tool
- **[exec-script-environment-requirements.md](exec-script-environment-requirements.md)** — adding or modifying exec scripts that call Claude, debugging missing API key errors in CI workflows, adding new workflow steps that run exec scripts
- **[formatter-tools.md](formatter-tools.md)** — formatting code, choosing a formatter, fixing format errors
- **[formatting-workflow.md](formatting-workflow.md)** — unsure whether to run make format or make prettier, encountering CI formatting failures, working with multiple file types in a PR, setting up CI iteration workflow
- **[git-force-push-decision-tree.md](git-force-push-decision-tree.md)** — encountering 'git push' rejected with 'fetch first' error, dealing with divergent branches after rebase or squash, deciding whether force push is safe, debugging PR update workflows
- **[github-actions-claude-integration.md](github-actions-claude-integration.md)** — running Claude in GitHub Actions workflows, configuring non-interactive Claude execution, capturing Claude output in CI
- **[github-actions-label-filtering.md](github-actions-label-filtering.md)** — debugging why label-based CI gating isn't working, implementing label-based workflow conditions, confused about .\*.name syntax vs array filtering
- **[github-actions-label-queries.md](github-actions-label-queries.md)** — checking PR labels in GitHub Actions workflows, working with push event workflows, implementing CI gating based on PR labels
- **[github-actions-output-patterns.md](github-actions-output-patterns.md)** — setting outputs in GitHub Actions workflows, passing data between workflow steps, handling multi-line content in GITHUB_OUTPUT, parsing JSON from workflow step outputs
- **[github-actions-security.md](github-actions-security.md)** — writing or modifying GitHub Actions workflow files, passing dynamic values to shell commands in workflows, using user-controlled input in GitHub Actions run blocks
- **[github-actions-workflow-patterns.md](github-actions-workflow-patterns.md)** — writing GitHub Actions workflows, debugging workflow conditions, composing step conditions
- **[github-cli-comment-patterns.md](github-cli-comment-patterns.md)** — Posting formatted PR comments from GitHub Actions workflows, Debugging escape sequences in `gh pr comment` commands, Encountering "Argument list too long" errors when passing content to CLI commands, Writing GitHub Actions steps that use `gh pr` commands with multi-line content
- **[github-commit-indexing-timing.md](github-commit-indexing-timing.md)** — working with GitHub commit status API, debugging 422 'No commit found for SHA' errors, implementing CI verification workflows
- **[github-token-scopes.md](github-token-scopes.md)** — deciding which token to use in GitHub Actions workflows, encountering permission errors with github.token, understanding why gist creation or user API calls fail
- **[label-rename-checklist.md](label-rename-checklist.md)** — renaming a GitHub label used in CI automation, updating label references across the codebase, debugging why CI label checks aren't working after a rename
- **[learn-ci-environment-detection.md](learn-ci-environment-detection.md)** — running /erk:learn in CI, understanding CI vs interactive mode differences, debugging learn workflow in GitHub Actions
- **[makefile-prettier-ignore-path.md](makefile-prettier-ignore-path.md)** — creating .prettierignore file, adding patterns to exclude files from Prettier, debugging why .prettierignore has no effect
- **[markdown-formatting.md](markdown-formatting.md)** — editing markdown files, handling Prettier CI failures, implementing documentation changes
- **[plan-implement-change-detection.md](plan-implement-change-detection.md)** — maintaining erk-impl workflow, debugging change detection issues, understanding why no-changes was triggered
- **[plan-implement-customization.md](plan-implement-customization.md)** — customizing erk-impl workflow for a specific repository, installing system dependencies in erk-impl CI, overriding Python version in erk-impl workflow
- **[plan-implement-workflow-patterns.md](plan-implement-workflow-patterns.md)** — modifying erk-impl workflow, adding cleanup steps to GitHub Actions, working with git reset in workflows
- **[prompt-patterns.md](prompt-patterns.md)** — Using Claude Code in GitHub Actions workflows, Creating multi-line prompts in CI YAML, Adding new prompts to the erk bundle
- **[review-spec-format.md](review-spec-format.md)** — creating a new code review, understanding why review specs follow certain patterns, debugging review behavior or structure
- **[review-types-taxonomy.md](review-types-taxonomy.md)** — creating a new review workflow, deciding whether to extend an existing review or create a new one, understanding review scope boundaries
- **[workflow-gating-patterns.md](workflow-gating-patterns.md)** — adding conditional execution to GitHub Actions workflows, implementing label-based CI skipping, understanding why CI was skipped on a PR
- **[workflow-model-policy.md](workflow-model-policy.md)** — creating or modifying GitHub Actions workflows that invoke Claude, choosing which Claude model to use in a workflow, understanding why all workflows default to Opus
- **[workflow-naming-conventions.md](workflow-naming-conventions.md)** — creating new GitHub Actions workflows launchable via erk launch, understanding the relationship between CLI names and workflow files
