<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Cli Documentation

- **[activation-scripts.md](activation-scripts.md)** — working with worktree environment setup, understanding .erk/activate.sh scripts, configuring post-create commands
- **[ambiguity-resolution.md](ambiguity-resolution.md)** — implementing CLI commands that accept identifiers with multiple possible matches, designing CLI behavior for ambiguous input, displaying tables of options without interactive selection
- **[auto-generated-reference-docs.md](auto-generated-reference-docs.md)** — adding or modifying CLI commands, changing erk exec command structure, encountering outdated exec reference docs
- **[checkout-helpers.md](checkout-helpers.md)** — writing checkout commands, creating worktrees in checkout commands, implementing branch checkout logic
- **[ci-aware-commands.md](ci-aware-commands.md)** — implementing commands that behave differently in CI, checking if code is running in GitHub Actions, skipping user-interactive steps in automated environments
- **[cli-options-validation.md](cli-options-validation.md)** — adding new CLI options or flags, implementing option validation logic, encountering unvalidated user input
- **[click-patterns.md](click-patterns.md)** — implementing CLI options with complex behavior, creating flags that optionally accept values, designing CLI flags with default behaviors
- **[code-review-filtering.md](code-review-filtering.md)** — debugging false positives in code review, understanding keyword-only parameter exceptions, working with ABC/Protocol method validation
- **[codespace-patterns.md](codespace-patterns.md)** — implementing CLI commands that use codespaces, working with resolve_codespace() helper, handling codespace name resolution errors
- **[command-group-structure.md](command-group-structure.md)** — creating a new command group, adding commands to an existing group, understanding command file organization
- **[command-organization.md](command-organization.md)** — organizing CLI commands, understanding command structure, designing command hierarchies
- **[pr-summarize.md](pr-summarize.md)** — generating PR descriptions for existing PRs, updating PR body with plan context, understanding pr summarize vs pr submit
- **[pr-sync-divergence.md](pr-sync-divergence.md)** — resolving branch divergence from remote, fixing gt submit 'Branch has been updated remotely' errors, syncing local branch with remote tracking branch
- **[update-roadmap-step.md](update-roadmap-step.md)** — working with objective roadmap tables, updating step PR references, implementing plan-save workflow
- **[dependency-injection-patterns.md](dependency-injection-patterns.md)** — writing erk exec scripts, testing exec scripts that use gateways, understanding exec script architecture, migrating exec scripts from subprocess to gateways
- **[ensure-ideal-pattern.md](ensure-ideal-pattern.md)** — handling discriminated union returns in CLI commands, narrowing types from T | NonIdealState or T | ErrorType, working with PR lookups, branch detection, or API calls that return union types, seeing EnsureIdeal in code and wondering when to use it vs Ensure
- **[erk-exec-commands.md](erk-exec-commands.md)** — running erk exec subcommands, looking up erk exec syntax
- **[erkdesk-makefile-targets.md](erkdesk-makefile-targets.md)** — running erkdesk tests locally or in CI, adding new test commands to the Makefile, understanding erkdesk CI integration
- **[error-handling-antipatterns.md](error-handling-antipatterns.md)** — handling expected CLI failures, deciding between RuntimeError and UserFacingCliError, converting exception-based error handling to UserFacingCliError
- **[exec-command-patterns.md](exec-command-patterns.md)** — writing exec scripts with PR/issue output, building diagnostic messages, standardizing exec command output
- **[exec-script-discovery.md](exec-script-discovery.md)** — using erk exec commands, unsure what flags an exec command accepts
- **[exec-script-patterns.md](exec-script-patterns.md)** — Creating new exec CLI commands
- **[exec-script-schema-patterns.md](exec-script-schema-patterns.md)** — writing an exec script that produces JSON consumed by another script, debugging silent filtering failures in exec script pipelines, adding new fields to exec script JSON output
- **[fast-path-pattern.md](fast-path-pattern.md)** — implementing CLI commands that can skip expensive operations, adding fast path optimization to existing commands, understanding when to invoke Claude vs complete locally
- **[json-schema.md](json-schema.md)** — adding --json flag to CLI commands, parsing JSON output from erk commands, implementing kit CLI commands with JSON output
- **[json-serialization-patterns.md](json-serialization-patterns.md)** — implementing erk exec commands with JSON output, serializing dataclasses to JSON, handling datetime or tuple fields in JSON output, working with --format json option
- **[learn-plan-land-flow.md](learn-plan-land-flow.md)** — landing PRs associated with learn plans, understanding learn plan status transitions, working with tripwire documentation promotion
- **[list-formatting.md](list-formatting.md)** — formatting list output, designing list commands, ensuring consistent list display
- **[local-commands.md](local-commands.md)** — designing local commands, understanding local command taxonomy, creating audit or assessment commands
- **[local-remote-command-groups.md](local-remote-command-groups.md)** — creating commands with local and remote variants, using invoke_without_command=True pattern, migrating separate commands to a unified group
- **[objective-commands.md](objective-commands.md)** — working with erk objective commands, implementing objective reconcile functionality, understanding auto-advance objectives
- **[optional-arguments.md](optional-arguments.md)** — making a CLI argument optional, inferring CLI arguments from context, implementing branch-based argument defaults
- **[output-styling.md](output-styling.md)** — styling CLI output, using colors in CLI, formatting terminal output
- **[plan-implement.md](plan-implement.md)** — understanding the /erk:plan-implement command, implementing plans from GitHub issues, working with .impl/ folders, debugging plan execution failures
- **[pr-operations.md](pr-operations.md)** — creating PRs programmatically, implementing PR submission workflows, preventing duplicate PR creation
- **[pr-submission.md](pr-submission.md)** — submitting PRs without Graphite, using /erk:git-pr-push command, understanding PR creation workflows
- **[pr-submit-pipeline.md](pr-submit-pipeline.md)** — modifying the PR submit workflow, adding new steps to the submit pipeline, debugging PR submission failures, understanding SubmitState or SubmitError
- **[session-management.md](session-management.md)** — using ${CLAUDE_SESSION_ID} in commands, debugging session ID errors, implementing session tracking, writing slash commands that need session context
- **[slash-command-exec-migration.md](slash-command-exec-migration.md)** — migrating slash commands to use erk exec, extracting manual logic from commands into exec scripts, understanding the exec command extraction pattern
- **[subprocess-stdin-patterns.md](subprocess-stdin-patterns.md)** — passing content to CLI tools via stdin, using subprocess with input parameter, CLI flags that only work with stdin
- **[template-variables.md](template-variables.md)** — configuring .env templates, using substitution variables in config.toml, setting environment variables per worktree, updating environment when switching worktrees
- **[two-phase-validation-model.md](two-phase-validation-model.md)** — implementing commands with multiple confirmations, designing commands that perform destructive mutations, working on erk land or similar multi-step commands
- **[workflow-commands.md](workflow-commands.md)** — triggering GitHub Actions workflows from CLI, using erk launch, understanding WORKFLOW_COMMAND_MAP
