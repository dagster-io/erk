---
title: Testing Tripwires
read_when:
  - "working on testing code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from testing/*.md frontmatter -->

# Testing Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before accessing FakeGit properties in tests** → Read [Erk Test Reference](testing.md) first. FakeGit has top-level properties (e.g., `git.staged_files`, `git.deleted_branches`, `git.added_worktrees`). Worktree operations delegate to an internal FakeWorktree sub-gateway.

**CRITICAL: Before adding a test for a new pipeline step without creating a dedicated test file** → Read [Submit Pipeline Test Organization](submit-pipeline-tests.md) first. Each pipeline step gets its own test file in tests/unit/cli/commands/pr/submit_pipeline/. Follow the one-file-per-step convention.

**CRITICAL: Before allowing `import X as Y` because it's a common convention (e.g., `import pandas as pd`)** → Read [Import Alias vs Re-Export Detection](alias-verification-pattern.md) first. Erk prohibits ALL gratuitous import aliases. The only exception is resolving genuine name collisions between two modules.

**CRITICAL: Before asking devrun agent to fix errors or make tests pass** → Read [Devrun Agent - Read-Only Design](devrun-agent.md) first. Devrun is READ-ONLY. It runs commands and reports results. The parent agent must handle all fixes.

**CRITICAL: Before creating a PreToolUse hook** → Read [Hook Testing Patterns](hook-testing.md) first. Test against edge cases. Untested hooks fail silently (exit 0, no output). Read docs/learned/testing/hook-testing.md first.

**CRITICAL: Before creating a fake gateway without constructor-injected error configuration** → Read [Gateway Fake Testing Exemplar](gateway-fake-testing-exemplar.md) first. Fakes must accept error variants at construction time (e.g., push_to_remote_error=PushError(...)) to enable failure injection in tests.

**CRITICAL: Before creating inline PlanRow test data with all fields** → Read [Erkdesk Component Test Architecture](erkdesk-component-testing.md) first. Use the makePlan() factory with Partial<PlanRow> overrides. PlanRow has 18+ fields; inline objects go stale when the type changes. See any test file for the pattern.

**CRITICAL: Before flagging `import X as X` or `from .mod import Y as Y` as a violation** → Read [Import Alias vs Re-Export Detection](alias-verification-pattern.md) first. The `X as X` form is an explicit re-export marker, not an alias. Only flag when the alias differs from the original name.

**CRITICAL: Before forgetting shouldAdvanceTime option when manually advancing** → Read [Vitest Fake Timers with Promises](vitest-fake-timers-with-promises.md) first. Use vi.useFakeTimers({ shouldAdvanceTime: true }) to enable manual timer control with advanceTimersByTimeAsync().

**CRITICAL: Before forgetting vi.useRealTimers() in afterEach()** → Read [Vitest Fake Timers with Promises](vitest-fake-timers-with-promises.md) first. Always restore real timers in afterEach(). Fake timers persist across tests and cause unpredictable failures.

**CRITICAL: Before implementing interactive prompts with ctx.console.confirm()** → Read [Erk Test Reference](testing.md) first. Ensure FakeConsole in test fixture is configured with `confirm_responses` parameter. See tests/commands/submit/test_existing_branch_detection.py for examples.

**CRITICAL: Before importing FakePromptExecutor from erk_shared.gateway.prompt_executor.fake** → Read [FakePromptExecutor API Migration - Gateway to Core](fake-api-migration-pattern.md) first. This module was deleted in the consolidation. Import from tests.fakes.prompt_executor or erk_shared.core.fakes instead.

**CRITICAL: Before modifying business logic in src/ without adding a test** → Read [Erk Test Reference](testing.md) first. Bug fixes require regression tests (fails before, passes after). Features require behavior tests.

**CRITICAL: Before passing group-level options when invoking a subcommand in tests** → Read [Command Group Testing](command-group-testing.md) first. Click does NOT propagate group-level options to subcommands by default. Options placed before the subcommand name in the args list are silently ignored.

**CRITICAL: Before passing string values to comments_with_urls parameter of FakeGitHubIssues** → Read [FakeGitHubIssues Dual-Comment Parameters](fake-github-testing.md) first. comments_with_urls requires IssueComment objects, not strings. Strings cause silent empty-list returns. Match the parameter to the ABC getter method your code calls.

**CRITICAL: Before running pytest, ty, ruff, prettier, make, or gt directly via Bash** → Read [Devrun Agent - Read-Only Design](devrun-agent.md) first. Use Task(subagent_type='devrun') instead. A UserPromptSubmit hook enforces this on every turn.

**CRITICAL: Before setting mock return values in test beforeEach** → Read [Window Mock Patterns for Electron IPC Testing](window-mock-patterns.md) first. Order matters: call mockReset() FIRST (clears previous test's values), THEN mockResolvedValue(). Reverse order has no effect.

**CRITICAL: Before testing IPC calls in a component test for a prop-driven component** → Read [Erkdesk Component Test Architecture](erkdesk-component-testing.md) first. PlanList and ActionToolbar receive data via props — they don't call window.erkdesk directly. IPC verification belongs in App.test.tsx where the actual fetch-state-props flow lives.

**CRITICAL: Before testing code that reads from Path.home() or ~/.claude/ or ~/.erk/** → Read [Exec Script Testing Patterns](exec-script-testing.md) first. Tests that run in parallel must use monkeypatch to isolate from real filesystem state. Functions like extract_slugs_from_session() cause flakiness when they read from the user's home directory.

**CRITICAL: Before testing components that use window.erkdesk IPC bridge** → Read [Window Mock Patterns for Electron IPC Testing](window-mock-patterns.md) first. Mock window.erkdesk in setup.ts, but always call mockReset() in beforeEach before setting mockResolvedValue(). Forgetting this causes mock value contamination - tests pass individually but fail in CI.

**CRITICAL: Before testing keyboard navigation in a component test** → Read [Erkdesk Component Test Architecture](erkdesk-component-testing.md) first. Keyboard handlers (j/k) are registered on document in App, not on individual components. Test keyboard navigation in App.test.tsx, not component tests.

**CRITICAL: Before testing only the subcommand path of a group with invoke_without_command=True** → Read [Command Group Testing](command-group-testing.md) first. Groups with default behavior need tests for BOTH paths: direct invocation (no subcommand) and explicit subcommand invocation. Missing either path is a coverage gap.

**CRITICAL: Before using Path.home() directly in production code** → Read [Exec Script Testing Patterns](exec-script-testing.md) first. Use gateway abstractions instead. For ~/.claude/ paths use ClaudeInstallation, for ~/.erk/ paths use ErkInstallation. Direct Path.home() access bypasses testability (fakes) and creates parallel test flakiness.

**CRITICAL: Before using monkeypatch.chdir() in exec script tests** → Read [Exec Script Testing Patterns](exec-script-testing.md) first. Use obj=ErkContext.for_test(cwd=tmp_path) instead. monkeypatch.chdir() doesn't inject context, causing 'Context not initialized' errors.

**CRITICAL: Before using output=, should_fail=, or transient_failures= parameters in FakePromptExecutor** → Read [FakePromptExecutor API Migration - Gateway to Core](fake-api-migration-pattern.md) first. These are the deleted gateway API. Use simulated\_\* parameters (tests/fakes/) or prompt_results/streaming_events (erk_shared/core/fakes.py). See migration table.

**CRITICAL: Before using vi.advanceTimersByTime() with Promise-based code** → Read [Vitest Fake Timers with Promises](vitest-fake-timers-with-promises.md) first. Use await vi.advanceTimersByTimeAsync() instead. Synchronous advancement blocks Promise microtasks and causes test hangs.

**CRITICAL: Before writing React component tests with Vitest + jsdom** → Read [jsdom DOM API Stubs for Vitest](vitest-jsdom-stubs.md) first. jsdom doesn't implement Element.prototype.scrollIntoView(). Stub in setup.ts with `Element.prototype.scrollIntoView = vi.fn()` before tests run to avoid TypeError.
