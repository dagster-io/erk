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

**adding a test for a new pipeline step without creating a dedicated test file** → Read [Submit Pipeline Test Organization](submit-pipeline-tests.md) first. Each pipeline step gets its own test file in tests/unit/cli/commands/pr/submit_pipeline/. Follow the one-file-per-step convention.

**adding monkeypatch or @patch to a test** → Read [Monkeypatch Elimination Checklist](monkeypatch-elimination-checklist.md) first. Use gateway fakes instead. If no gateway exists for the operation, create one first. See gateway-abc-implementation.md.

**allowing `import X as Y` because it's a common convention (e.g., `import pandas as pd`)** → Read [Import Alias vs Re-Export Detection](alias-verification-pattern.md) first. Erk prohibits ALL gratuitous import aliases. The only exception is resolving genuine name collisions between two modules.

**asking devrun agent to fix errors or make tests pass** → Read [Devrun Agent - Read-Only Design](devrun-agent.md) first. Devrun is READ-ONLY. It runs commands and reports results. The parent agent must handle all fixes.

**creating a fake gateway without constructor-injected error configuration** → Read [Gateway Fake Testing Exemplar](gateway-fake-testing-exemplar.md) first. Fakes must accept error variants at construction time (e.g., push_to_remote_error=PushError(...)) to enable failure injection in tests.

**creating a fake that uses **init** when frozen dataclass would work** → Read [Frozen Dataclass Test Doubles](frozen-dataclass-test-doubles.md) first. FakeBranchManager uses frozen dataclass because its state is simple and declarative. FakeGitHub uses **init** because it has 30+ constructor params. Choose based on complexity.

**creating inline PlanRow test data with all fields** → Read [Erkdesk Component Test Architecture](erkdesk-component-testing.md) first. Use the makePlan() factory with Partial<PlanRow> overrides. PlanRow has 18+ fields; inline objects go stale when the type changes. See any test file for the pattern.

**creating or modifying a hook** → Read [Hook Testing Patterns](hook-testing.md) first. Hooks fail silently (exit 0, no output) — untested hooks are invisible failures. Read docs/learned/testing/hook-testing.md first.

**duplicating the \_make_state helper between test files** → Read [Submit Pipeline Test Organization](submit-pipeline-tests.md) first. Each test file has its own \_make_state with step-appropriate defaults (e.g., finalize tests default pr_number=42, extract_diff tests default pr_number=None). This is intentional — different steps need different pre-conditions.

**exposing a mutation tracking list directly as a property without copying** → Read [Frozen Dataclass Test Doubles](frozen-dataclass-test-doubles.md) first. Return list(self.\_tracked_list) from properties, not self.\_tracked_list. Direct exposure lets test code accidentally mutate the tracking state.

**flagging `import X as X` or `from .mod import Y as Y` as a violation** → Read [Import Alias vs Re-Export Detection](alias-verification-pattern.md) first. The `X as X` form is an explicit re-export marker, not an alias. Only flag when the alias differs from the original name.

**implementing interactive prompts with ctx.console.confirm()** → Read [Erk Test Reference](testing.md) first. Ensure FakeConsole in test fixture is configured with `confirm_responses` parameter. See tests/commands/submit/test_existing_branch_detection.py for examples.

**importing FakePromptExecutor from erk_shared.gateway.prompt_executor.fake** → Read [FakePromptExecutor API Migration - Gateway to Core](fake-api-migration-pattern.md) first. This module was deleted in the consolidation. Import from tests.fakes.prompt_executor or erk_shared.core.fakes instead.

**mocking a browser API in an individual test file** → Read [jsdom DOM API Stubs for Vitest](vitest-jsdom-stubs.md) first. Environment-level API stubs belong in setup.ts (runs before all tests), not in individual test files. Only mock behavior-specific values (like IPC responses) per-test.

**modifying business logic in src/ without adding a test** → Read [Erk Test Reference](testing.md) first. Bug fixes require regression tests (fails before, passes after). Features require behavior tests.

**passing group-level options when invoking a subcommand in tests** → Read [Command Group Testing](command-group-testing.md) first. Click does NOT propagate group-level options to subcommands by default. Options placed before the subcommand name in the args list are silently ignored.

**passing string values to comments_with_urls parameter of FakeGitHubIssues** → Read [FakeGitHubIssues Dual-Comment Parameters](fake-github-testing.md) first. comments_with_urls requires IssueComment objects, not strings. Strings cause silent empty-list returns. Match the parameter to the ABC getter method your code calls.

**resetting mocks in afterEach instead of beforeEach** → Read [Vitest Mock Reset Discipline for Shared Global Mocks](window-mock-patterns.md) first. Use beforeEach for mock resets, not afterEach. If a test throws before afterEach runs, the mock remains contaminated for the next test.

**running pytest, ty, ruff, prettier, make, or gt directly via Bash** → Read [Devrun Agent - Read-Only Design](devrun-agent.md) first. Use Task(subagent_type='devrun') instead. A UserPromptSubmit hook enforces this on every turn.

**setting mock return values in test beforeEach without calling mockReset() first** → Read [Vitest Mock Reset Discipline for Shared Global Mocks](window-mock-patterns.md) first. Always call mockReset() BEFORE mockResolvedValue(). Without reset, previous test's mock values persist — causing tests to pass individually but fail in CI due to cross-test contamination.

**testing IPC calls in a component test for a prop-driven component** → Read [Erkdesk Component Test Architecture](erkdesk-component-testing.md) first. PlanList and ActionToolbar receive data via props — they don't call window.erkdesk directly. IPC verification belongs in App.test.tsx where the actual fetch-state-props flow lives.

**testing a pipeline step by running the full pipeline** → Read [Submit Pipeline Test Organization](submit-pipeline-tests.md) first. Test steps in isolation by calling the step function directly. Only test_run_pipeline.py exercises the runner. Step tests pre-populate state as if prior steps succeeded.

**testing code that reads from Path.home() or ~/.claude/ or ~/.erk/** → Read [Exec Script Testing Patterns](exec-script-testing.md) first. Tests that run in parallel must use monkeypatch to isolate from real filesystem state. Functions like extract_slugs_from_session() cause flakiness when they read from the user's home directory.

**testing keyboard navigation in a component test** → Read [Erkdesk Component Test Architecture](erkdesk-component-testing.md) first. Keyboard handlers (j/k) are registered on document in App, not on individual components. Test keyboard navigation in App.test.tsx, not component tests.

**testing only the subcommand path of a group with invoke_without_command=True** → Read [Command Group Testing](command-group-testing.md) first. Groups with default behavior need tests for BOTH paths: direct invocation (no subcommand) and explicit subcommand invocation. Missing either path is a coverage gap.

**tracking mutations before checking error configuration in a fake method** → Read [Gateway Fake Testing Exemplar](gateway-fake-testing-exemplar.md) first. Decide deliberately: should this operation track even on failure? push_to_remote skips tracking on error (nothing happened), pull_rebase always tracks (the attempt matters). Match the real operation's semantics.

**tracking only the primary argument in a mutation tuple, omitting flags or options** → Read [Frozen Dataclass Test Doubles](frozen-dataclass-test-doubles.md) first. Track ALL call parameters in tuples (e.g., (branch, force) not just branch). Lost context leads to undertested behavior.

**using Path.home() directly in production code** → Read [Exec Script Testing Patterns](exec-script-testing.md) first. Use gateway abstractions instead. For ~/.claude/ paths use ClaudeInstallation, for ~/.erk/ paths use ErkInstallation. Direct Path.home() access bypasses testability (fakes) and creates parallel test flakiness.

**using monkeypatch or unittest.mock in hook tests** → Read [Hook Testing Patterns](hook-testing.md) first. Use ErkContext.for_test() with CliRunner instead of mocking. See docs/learned/testing/hook-testing.md.

**using monkeypatch to stub Path.home() or subprocess.run()** → Read [Monkeypatch Elimination Checklist](monkeypatch-elimination-checklist.md) first. These are the two most common monkeypatch targets. Both have established gateway replacements — ClaudeInstallation/ErkInstallation for paths, specific gateways for subprocess.

**using monkeypatch.chdir() in exec script tests** → Read [Exec Script Testing Patterns](exec-script-testing.md) first. Use obj=ErkContext.for_test(cwd=tmp_path) instead. monkeypatch.chdir() doesn't inject context, causing 'Context not initialized' errors.

**using output=, should_fail=, or transient_failures= parameters in FakePromptExecutor** → Read [FakePromptExecutor API Migration - Gateway to Core](fake-api-migration-pattern.md) first. These are the deleted gateway API. Use simulated\_\* parameters (tests/fakes/) or prompt_results/streaming_events (erk_shared/core/fakes.py). See migration table.

**using truthiness checks or .success on discriminated union results in tests** → Read [Gateway Fake Testing Exemplar](gateway-fake-testing-exemplar.md) first. Always use isinstance() for type narrowing. Never check bool(result) or result.success — these bypass the type system.

**using vi.advanceTimersByTime() in a test with Promise-based code** → Read [Vitest Fake Timers with Promises](vitest-fake-timers-with-promises.md) first. Use await vi.advanceTimersByTimeAsync() instead. The synchronous variant blocks Promise microtask flushing, causing hangs or silently skipped callbacks.

**using vi.useFakeTimers() without restoring in afterEach** → Read [Vitest Fake Timers with Promises](vitest-fake-timers-with-promises.md) first. Always call vi.useRealTimers() in afterEach(). Fake timers leak across tests and cause unpredictable failures in unrelated test suites.

**writing React component tests with Vitest + jsdom** → Read [jsdom DOM API Stubs for Vitest](vitest-jsdom-stubs.md) first. jsdom doesn't implement several browser APIs (scrollIntoView, ResizeObserver). Check erkdesk/src/test/setup.ts for existing stubs before adding new ones.
