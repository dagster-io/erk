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

**CRITICAL: Before Test only success cases for batch commands** → Read [Exec Script Batch Testing](exec-script-batch-testing.md) first. Cover: all success, partial failure, validation errors, and JSON structure. See test organization categories.

**CRITICAL: Before accessing FakeGit properties in tests** → Read [Erk Test Reference](testing.md) first. FakeGit has top-level properties (e.g., `git.staged_files`, `git.deleted_branches`, `git.added_worktrees`). Worktree operations delegate to an internal FakeWorktree sub-gateway.

**CRITICAL: Before adding a test for a new pipeline step without creating a dedicated test file** → Read [Submit Pipeline Test Organization](submit-pipeline-tests.md) first. Each pipeline step gets its own test file in tests/unit/cli/commands/pr/submit_pipeline/. Follow the one-file-per-step convention.

**CRITICAL: Before asking devrun agent to fix errors or make tests pass** → Read [Devrun Agent - Read-Only Design](devrun-agent.md) first. Devrun is READ-ONLY. It runs commands and reports results. The parent agent must handle all fixes.

**CRITICAL: Before creating a PreToolUse hook** → Read [Hook Testing Patterns](hook-testing.md) first. Test against edge cases. Untested hooks fail silently (exit 0, no output). Read docs/learned/testing/hook-testing.md first.

**CRITICAL: Before creating a fake gateway without constructor-injected error configuration** → Read [Gateway Fake Testing Exemplar](gateway-fake-testing-exemplar.md) first. Fakes must accept error variants at construction time (e.g., push_to_remote_error=PushError(...)) to enable failure injection in tests.

**CRITICAL: Before forgetting shouldAdvanceTime option when manually advancing** → Read [Vitest Fake Timers with Promises](vitest-fake-timers-with-promises.md) first. Use vi.useFakeTimers({ shouldAdvanceTime: true }) to enable manual timer control with advanceTimersByTimeAsync().

**CRITICAL: Before forgetting vi.useRealTimers() in afterEach()** → Read [Vitest Fake Timers with Promises](vitest-fake-timers-with-promises.md) first. Always restore real timers in afterEach(). Fake timers persist across tests and cause unpredictable failures.

**CRITICAL: Before implementing interactive prompts with ctx.console.confirm()** → Read [Erk Test Reference](testing.md) first. Ensure FakeConsole in test fixture is configured with `confirm_responses` parameter. See tests/commands/submit/test_existing_branch_detection.py for examples.

**CRITICAL: Before modifying business logic in src/ without adding a test** → Read [Erk Test Reference](testing.md) first. Bug fixes require regression tests (fails before, passes after). Features require behavior tests.

**CRITICAL: Before setting mock return values in test beforeEach** → Read [Window Mock Patterns for Electron IPC Testing](window-mock-patterns.md) first. Order matters: call mockReset() FIRST (clears previous test's values), THEN mockResolvedValue(). Reverse order has no effect.

**CRITICAL: Before testing code that reads from Path.home() or ~/.claude/ or ~/.erk/** → Read [Exec Script Testing Patterns](exec-script-testing.md) first. Tests that run in parallel must use monkeypatch to isolate from real filesystem state. Functions like extract_slugs_from_session() cause flakiness when they read from the user's home directory.

**CRITICAL: Before testing components that use window.erkdesk IPC bridge** → Read [Window Mock Patterns for Electron IPC Testing](window-mock-patterns.md) first. Mock window.erkdesk in setup.ts, but always call mockReset() in beforeEach before setting mockResolvedValue(). Forgetting this causes mock value contamination - tests pass individually but fail in CI.

**CRITICAL: Before using Path.home() directly in production code** → Read [Exec Script Testing Patterns](exec-script-testing.md) first. Use gateway abstractions instead. For ~/.claude/ paths use ClaudeInstallation, for ~/.erk/ paths use ErkInstallation. Direct Path.home() access bypasses testability (fakes) and creates parallel test flakiness.

**CRITICAL: Before using monkeypatch.chdir() in exec script tests** → Read [Exec Script Testing Patterns](exec-script-testing.md) first. Use obj=ErkContext.for_test(cwd=tmp_path) instead. monkeypatch.chdir() doesn't inject context, causing 'Context not initialized' errors.

**CRITICAL: Before using old FakePromptExecutor API patterns in new tests** → Read [Fake API Migration Pattern - PromptExecutor Consolidation](fake-api-migration-pattern.md) first. Use simulated\_\* parameters (new API), not output=/should_fail= (old gateway API). See migration table.

**CRITICAL: Before using vi.advanceTimersByTime() with Promise-based code** → Read [Vitest Fake Timers with Promises](vitest-fake-timers-with-promises.md) first. Use await vi.advanceTimersByTimeAsync() instead. Synchronous advancement blocks Promise microtasks and causes test hangs.

**CRITICAL: Before writing React component tests with Vitest + jsdom** → Read [jsdom DOM API Stubs for Vitest](vitest-jsdom-stubs.md) first. jsdom doesn't implement Element.prototype.scrollIntoView(). Stub in setup.ts with `Element.prototype.scrollIntoView = vi.fn()` before tests run to avoid TypeError.
