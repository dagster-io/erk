---
title: Testing Tripwires
read_when:
  - "working on testing code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from testing/*.md frontmatter -->

# Testing Tripwires

Rules triggered by matching actions in code.

**Test only success cases for batch commands** → Read [Exec Script Batch Testing](exec-script-batch-testing.md) first. Cover all four categories: success, partial failure, validation errors, and JSON structure. Missing any category leaves a critical gap.

**Use stateful failure injection (\_should_fail_next flags) in fake gateways** → Read [Exec Script Batch Testing](exec-script-batch-testing.md) first. Use set-based constructor injection instead. Stateful flags are order-dependent and brittle. See the set-based pattern below.

**accessing FakeGit properties in tests** → Read [Erk Test Reference](testing.md) first. FakeGit has top-level properties (e.g., `git.staged_files`, `git.deleted_branches`, `git.added_worktrees`). Worktree operations delegate to an internal FakeWorktree sub-gateway.

**adding a force-include entry without registering in codex_portable_skills()** → Read [Artifact Distribution Sync Testing](artifact-distribution-sync.md) first. The skill will be distributed but not recognized by the runtime. Add it to codex_portable_skills() in src/erk/core/capabilities/codex_portable.py.

**adding a skill to codex_portable_skills() without a pyproject.toml force-include entry** → Read [Artifact Distribution Sync Testing](artifact-distribution-sync.md) first. The wheel won't contain the skill. Add a force-include entry in pyproject.toml [tool.hatch.build.targets.wheel.force-include]. test_codex_portable_skills_match_force_include will catch this.

**adding a test for a new pipeline step without creating a dedicated test file** → Read [Submit Pipeline Test Organization](submit-pipeline-tests.md) first. Each pipeline step gets its own test file in tests/unit/cli/commands/pr/submit_pipeline/. Follow the one-file-per-step convention.

**adding a tracking list without documenting the tuple field order** → Read [FakeGitHub Mutation Tracking](fake-github-mutation-tracking.md) first. Every tracking list must have a property docstring specifying the tuple format (e.g., 'Returns list of (pr_number, label) tuples'). Without it, test authors guess field positions wrong.

**adding monkeypatch or @patch to a test** [pattern: `@patch|monkeypatch\.`] → Read [Monkeypatch Elimination Checklist](monkeypatch-elimination-checklist.md) first. Use gateway fakes instead. If no gateway exists for the operation, create one first. See gateway-abc-implementation.md.

**adding new parameters to gateway methods without truth-table test coverage** → Read [Exec Script Testing Patterns](exec-script-testing.md) first. When adding boolean parameters to gateway methods, the truth-table testing pattern covers all boolean combinations. Bot reviewers enforce this coverage.

**allowing `import X as Y` because it's a common convention (e.g., `import pandas as pd`)** → Read [Import Alias vs Re-Export Detection](alias-verification-pattern.md) first. Erk prohibits ALL gratuitous import aliases. The only exception is resolving genuine name collisions between two modules.

**asking devrun agent to fix errors or make tests pass** → Read [Devrun Agent - Read-Only Design](devrun-agent.md) first. Devrun is READ-ONLY. It runs commands and reports results. The parent agent must handle all fixes.

**asserting on FakeGitHubIssues.added_comments for PlannedPRBackend.add_comment()** → Read [FakeGitHubIssues Dual-Comment Parameters](fake-github-testing.md) first. PlannedPRBackend routes comments to PR comments (FakeGitHub.pr_comments), not issue comments (FakeGitHubIssues.added_comments). Check the correct fake when testing planned-PR comment operations.

**asserting on YAML metadata field values with exact string matching** → Read [Erk Test Reference](testing.md) first. Assert on key-only format ('field_name:'), not 'field_name: "value"'. YAML serialization differs from Python repr.

**asserting on fake-specific properties in tests using `build_workspace_test_context` with `use_graphite=True`** → Read [Erk Test Reference](testing.md) first. Production wrappers (e.g., `GraphiteBranchManager`) do not expose fake tracking properties like `submitted_branches`. Assert on observable behavior (CLI output, return values) instead of accessing fake internals through the wrapper.

**asserting user_output() content against capsys stdout** → Read [Erk Test Reference](testing.md) first. user_output() routes to stderr. When testing code that calls user_output(), assert against capsys.readouterr().err, not .out.

**calling get_bundled_claude_dir() inside a testable function** → Read [Bundled Path Parameter Injection for Testability](parameter-injection-pattern.md) first. Accept bundled_claude_dir as a parameter instead. Production callers pass get_bundled_claude_dir(), tests pass tmp_path / 'bundled'. Read this doc.

**changing cleanup or deletion behavior without updating test assertions** → Read [Erk Test Reference](testing.md) first. When behavior changes from 'delete X' to 'preserve X', update test assertions to verify the new behavior (e.g., assert file persists instead of asserting it was deleted). Stale assertions silently validate the old behavior.

**choosing between monkeypatch and fakes for a test** → Read [Monkeypatch vs Fakes Decision Guide](monkeypatch-vs-fakes-decision.md) first. Read monkeypatch-vs-fakes-decision.md first. Default to gateway fakes. Monkeypatch is only appropriate for process-level globals like Path.home() in exec scripts.

**creating ErkPackageInfo directly in production code** → Read [ErkPackageInfo Value Object](erk-package-info-pattern.md) first. Use ErkPackageInfo.from_project_dir(). Direct construction is for tests only.

**creating FakeSessionData without gitBranch JSONL** → Read [Testing with FakeClaudeInstallation](session-store-testing.md) first. Missing `gitBranch` field causes silent empty results from branch-filtered discovery. Always include gitBranch in fake session data.

**creating a FakeGitHub PR without checking auto-registration in \_pr_details** → Read [FakeGitHub API Reference](fake-github-api-reference.md) first. FakeGitHub.create_pr() auto-registers the PR in \_pr_details. Manually adding to \_pr_details after create_pr() causes duplicates.

**creating a FakePlanBackend for testing caller code** → Read [Backend Testing Composition](backend-testing-composition.md) first. Use real backend + fake gateway instead. FakeGitHub injected into PlannedPRBackend. Fake backends are only for validating ABC contract across providers.

**creating a fake gateway without constructor-injected error configuration** → Read [Gateway Fake Testing Exemplar](gateway-fake-testing-exemplar.md) first. Fakes must accept error variants at construction time (e.g., push_to_remote_error=PushError(...)) to enable failure injection in tests.

**creating a fake that uses **init** when frozen dataclass would work** → Read [Frozen Dataclass Test Doubles](frozen-dataclass-test-doubles.md) first. FakeBranchManager uses frozen dataclass because its state is simple and declarative. FakeGitHub uses **init** because it has 30+ constructor params. Choose based on complexity.

**creating a test file exceeding 500 lines** → Read [Test File Organization Pattern](test-file-organization.md) first. Consider splitting into a subdirectory module. See test-file-organization.md for the pattern and existing precedents.

**creating custom FakeGitHubIssues without passing to build_workspace_test_context** → Read [FakeGitHubIssues Dual-Comment Parameters](fake-github-testing.md) first. Always pass issues=issues to build_workspace_test_context when using custom FakeGitHubIssues. Without it, plan_backend operates on a different instance and metadata writes are invisible.

**creating or modifying a hook** → Read [Hook Testing Patterns](hook-testing.md) first. Hooks fail silently (exit 0, no output) — untested hooks are invisible failures. Read docs/learned/testing/hook-testing.md first.

**debugging 100+ unexpected test failures with no obvious cause** → Read [Environment Variable Isolation in Tests](environment-variable-isolation.md) first. Check ERK_PLAN_BACKEND first. Although the env var is now obsolete (get_plan_backend() was deleted in PR #7971), legacy code paths in context_for_test() may still read it. Use monkeypatch.delenv('ERK_PLAN_BACKEND', raising=False) or env_overrides={} in fixtures as a defensive measure until full cleanup in objective #7911.

**duplicating the \_make_state helper between test files** → Read [Submit Pipeline Test Organization](submit-pipeline-tests.md) first. Each test file has its own \_make_state with step-appropriate defaults (e.g., finalize tests default pr_number=42, extract_diff tests default pr_number=None). This is intentional — different steps need different pre-conditions.

**exposing a mutation tracking list directly as a property without copying** → Read [Frozen Dataclass Test Doubles](frozen-dataclass-test-doubles.md) first. Return list(self.\_tracked_list) from properties, not self.\_tracked_list. Direct exposure lets test code accidentally mutate the tracking state.

**flagging `import X as X` or `from .mod import Y as Y` as a violation** → Read [Import Alias vs Re-Export Detection](alias-verification-pattern.md) first. The `X as X` form is an explicit re-export marker, not an alias. Only flag when the alias differs from the original name.

**implementing interactive prompts with ctx.console.confirm()** → Read [Erk Test Reference](testing.md) first. Ensure FakeConsole in test fixture is configured with `confirm_responses` parameter. Array length must match prompt count exactly — too few causes IndexError, too many indicates a removed prompt. See tests/commands/submit/test_existing_branch_detection.py for examples.

**importing FakePromptExecutor from erk_shared.gateway.prompt_executor.fake** → Read [FakePromptExecutor API Migration - Gateway to Core](fake-api-migration-pattern.md) first. This module was deleted in the consolidation. Import from tests.fakes.prompt_executor or erk_shared.core.fakes instead.

**importing or monkeypatching a module with 'exec' in its path** → Read [Exec Script Testing Patterns](exec-script-testing.md) first. `exec` is a Python keyword that blocks direct import and string-path monkeypatch. Use `importlib.import_module()` + object-form `setattr` instead.

**modifying business logic in src/ without adding a test** → Read [Erk Test Reference](testing.md) first. Bug fixes require regression tests (fails before, passes after). Features require behavior tests.

**monkeypatching erk.tui.app.subprocess.Popen** → Read [TUI Subprocess Testing Patterns](tui-subprocess-testing.md) first. Monkeypatch subprocess.Popen at module level (subprocess.Popen), not erk.tui.app.subprocess.Popen. The import uses 'import subprocess' not 'from subprocess import Popen'.

**passing group-level options when invoking a subcommand in tests** → Read [Command Group Testing](command-group-testing.md) first. Click does NOT propagate group-level options to subcommands by default. Options placed before the subcommand name in the args list are silently ignored.

**passing mix_stderr parameter to CliRunner** → Read [CLI Testing Patterns](cli-testing.md) first. Click 8.3.1 CliRunner no longer accepts mix_stderr parameter. Use CliRunner() or CliRunner(env={}) instead.

**passing string values to comments_with_urls parameter of FakeGitHubIssues** → Read [FakeGitHubIssues Dual-Comment Parameters](fake-github-testing.md) first. comments_with_urls requires IssueComment objects, not strings. Strings cause silent empty-list returns. Match the parameter to the ABC getter method your code calls.

**renaming a user-facing string in CLI output and updating related test assertions** → Read [CLI Testing Patterns](cli-testing.md) first. Test assertion lag: after renaming display strings (e.g., 'issue' → 'plan'), grep all test files for the old literal before committing. Tests using old string literals against stale snapshots will silently pass — the failure only surfaces in CI on a clean checkout.

**running pytest, ty, ruff, prettier, make, or gt directly via Bash** → Read [Devrun Agent - Read-Only Design](devrun-agent.md) first. Use Task(subagent_type='devrun') instead. A UserPromptSubmit hook enforces this on every turn.

**testing a pipeline step by running the full pipeline** → Read [Submit Pipeline Test Organization](submit-pipeline-tests.md) first. Test steps in isolation by calling the step function directly. Only test_run_pipeline.py exercises the runner. Step tests pre-populate state as if prior steps succeeded.

**testing admin commands that read GitHub settings** → Read [Admin Command Testing Patterns](admin-command-testing.md) first. Use FakeGitHubAdmin with workflow_permissions dict to configure read state. Do not mock subprocess calls.

**testing branch-scoped impl directory code without configuring FakeGit current_branches** → Read [FakeGit Branch Divergence Testing](fake-git-divergence.md) first. FakeGit current_branches must be configured when testing resolve_impl_dir(). Without this, resolve_impl_dir() gets the wrong branch and resolves to the wrong directory.

**testing code that reads ERK_PLAN_BACKEND or other environment variables via CliRunner** → Read [CLI Testing Patterns](cli-testing.md) first. CliRunner env var isolation: ambient env vars from the developer shell leak into CliRunner by default and cause intermittent test failures. Use CliRunner(env={'ERK_PLAN_BACKEND': '...'}) to override, or CliRunner(env={}) to isolate completely. Never rely on ambient env being clean. Note: mix_stderr parameter is broken in Click 8.3.1 — do not use it.

**testing code that reads from Path.home() or ~/.claude/ or ~/.erk/** [pattern: `Path\.home\(\)`] → Read [Exec Script Testing Patterns](exec-script-testing.md) first. Tests that run in parallel must use monkeypatch to isolate from real filesystem state. Functions like extract_slugs_from_session() cause flakiness when they read from the user's home directory.

**testing divergence without setting branch_divergence in FakeGit** → Read [FakeGit Branch Divergence Testing](fake-git-divergence.md) first. FakeGit.is_branch_diverged_from_remote() returns from the branch_divergence dict. Missing entries return default (not diverged). Set explicit divergence state for each test scenario.

**testing only the subcommand path of a group with invoke_without_command=True** → Read [Command Group Testing](command-group-testing.md) first. Groups with default behavior need tests for BOTH paths: direct invocation (no subcommand) and explicit subcommand invocation. Missing either path is a coverage gap.

**testing subprocess-based TUI workers without capturing status bar updates** → Read [TUI Subprocess Testing Patterns](tui-subprocess-testing.md) first. Use app.call_from_thread assertions to verify status bar updates from background workers. Status bar updates are the primary user-facing output.

**tracking mutations before checking error configuration in a fake method** → Read [Gateway Fake Testing Exemplar](gateway-fake-testing-exemplar.md) first. Decide deliberately: should this operation track even on failure? push_to_remote skips tracking on error (nothing happened), pull_rebase always tracks (the attempt matters). Match the real operation's semantics.

**tracking only the primary argument in a mutation tuple, omitting flags or options** → Read [Frozen Dataclass Test Doubles](frozen-dataclass-test-doubles.md) first. Track ALL call parameters in tuples (e.g., (branch, force) not just branch). Lost context leads to undertested behavior.

**using Path.home() directly in production code** [pattern: `Path\.home\(\)`] → Read [Exec Script Testing Patterns](exec-script-testing.md) first. Use gateway abstractions instead. For ~/.claude/ paths use ClaudeInstallation, for ~/.erk/ paths use ErkInstallation. Direct Path.home() access bypasses testability (fakes) and creates parallel test flakiness.

**using branch names with '/' in test data for resolve_impl_dir() tests** → Read [Exec Script Testing Patterns](exec-script-testing.md) first. Branch name sanitization (\_sanitize_branch_for_dirname() at packages/erk-shared/src/erk_shared/impl_folder.py) replaces '/' with '--'. Test data must account for this: branch 'plnd/my-feature' becomes directory 'plnd--my-feature'.

**using context_for_test without matching parameter names to the current API** → Read [FakeGitHub API Reference](fake-github-api-reference.md) first. context_for_test() parameter names evolve. Check the current function signature before adding new parameters.

**using context_for_test() with wrong parameter name for issues** → Read [context_for_test() Dual Implementations](context-builder-signatures.md) first. erk-shared uses github_issues= parameter, src/erk uses issues= parameter. These are NOT interchangeable — using wrong name causes TypeError.

**using context_for_test() with wrong parameter name for issues** → Read [Erk Test Reference](testing.md) first. erk-shared uses github_issues= parameter, src/erk uses issues= parameter. These are NOT interchangeable — using wrong name causes TypeError.

**using isinstance() to detect plan backend type in application code** → Read [Plan Storage Testing](dual-backend-testing.md) first. Use plan_backend.get_provider_name() for backend-conditional logic (returns 'github-draft-pr'). isinstance checks couple to implementation classes. The provider name string is the stable API.

**using monkeypatch or unittest.mock in hook tests** → Read [Hook Testing Patterns](hook-testing.md) first. Use ErkContext.for_test() with CliRunner instead of mocking. See docs/learned/testing/hook-testing.md.

**using monkeypatch to set HOME in init command tests** → Read [env_overrides Pattern for erk_isolated_fs_env](env-overrides-pattern.md) first. Use erk_isolated_fs_env(runner, env_overrides={'HOME': '{root_worktree}'}) instead.

**using monkeypatch to stub Path.home() or subprocess.run()** [pattern: `monkeypatch\.setattr.*Path\.home|monkeypatch.*subprocess\.run`] → Read [Monkeypatch Elimination Checklist](monkeypatch-elimination-checklist.md) first. These are the two most common monkeypatch targets. Both have established gateway replacements — ClaudeInstallation/ErkInstallation for paths, specific gateways for subprocess.

**using monkeypatch.chdir() in exec script tests** [pattern: `monkeypatch\.chdir\(`] → Read [Exec Script Testing Patterns](exec-script-testing.md) first. Use obj=ErkContext.for_test(cwd=tmp_path) instead. monkeypatch.chdir() doesn't inject context, causing 'Context not initialized' errors.

**using output=, should_fail=, or transient_failures= parameters in FakePromptExecutor** → Read [FakePromptExecutor API Migration - Gateway to Core](fake-api-migration-pattern.md) first. These are the deleted gateway API. Use simulated\_\* parameters (tests/fakes/) or prompt_results/streaming_events (erk_shared/core/fakes.py). See migration table.

**using truthiness checks or .success on discriminated union results in tests** → Read [Gateway Fake Testing Exemplar](gateway-fake-testing-exemplar.md) first. Always use isinstance() for type narrowing. Never check bool(result) or result.success — these bypass the type system.

**writing plan storage tests that parametrize across both backends** → Read [Plan Storage Testing](dual-backend-testing.md) first. After PR #8210, only the PlannedPRBackend exists. The GitHubPlanStore class was deleted. New plan-related tests should use PlannedPRBackend directly.
