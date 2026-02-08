<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Testing Documentation

- **[alias-verification-pattern.md](alias-verification-pattern.md)** — enforcing the no-import-aliases rule, building automated alias detection, distinguishing re-exports from alias violations
- **[cli-test-error-assertions.md](cli-test-error-assertions.md)** — writing CLI tests with error assertions, testing error messages in Click commands, asserting on CLI output
- **[cli-testing.md](cli-testing.md)** — writing tests for erk CLI commands, using ErkContext.for_test(), testing Click commands with context
- **[command-group-testing.md](command-group-testing.md)** — testing Click command groups with invoke_without_command=True, writing tests for commands that serve as both group and default action
- **[devrun-agent.md](devrun-agent.md)** — using the devrun agent, running CI checks via Task tool, writing prompts for devrun, understanding the parent-agent fix cycle
- **[erkdesk-component-testing.md](erkdesk-component-testing.md)** — writing tests for erkdesk React components, deciding whether to test at component level or App level, adding keyboard navigation tests for erkdesk, creating test data factories for PlanRow
- **[exec-script-batch-testing.md](exec-script-batch-testing.md)** — writing tests for batch exec commands, organizing test cases for JSON stdin/stdout commands, adding failure injection to a fake gateway for batch operations
- **[exec-script-testing.md](exec-script-testing.md)** — testing exec CLI commands, writing integration tests for scripts, debugging 'Context not initialized' errors in tests, debugging flaky tests in parallel execution
- **[fake-api-migration-pattern.md](fake-api-migration-pattern.md)** — writing tests that use FakePromptExecutor, choosing between the two FakePromptExecutor implementations, encountering old-style output=/should_fail= patterns in test code
- **[fake-github-testing.md](fake-github-testing.md)** — setting up FakeGitHubIssues in a test, test fails with empty comments from FakeGitHubIssues, choosing between comments and comments_with_urls parameters
- **[frozen-dataclass-test-doubles.md](frozen-dataclass-test-doubles.md)** — implementing a fake for an ABC interface, adding mutation tracking to a test double, understanding the frozen dataclass with mutable internals pattern, writing tests that assert on method call parameters
- **[gateway-fake-testing-exemplar.md](gateway-fake-testing-exemplar.md)** — writing tests for gateway fakes with discriminated unions, implementing new fake gateway methods, testing success and error paths through fakes
- **[hook-testing.md](hook-testing.md)** — writing tests for a PreToolUse hook, testing hooks that read from stdin, testing hook exit code behavior
- **[import-conflict-resolution.md](import-conflict-resolution.md)** — resolving merge conflicts during rebase, fixing import conflicts after consolidation, rebasing after shared module changes
- **[integration-test-speed.md](integration-test-speed.md)** — integration test is slow, test takes too long, pytest --durations shows slow test
- **[integration-testing-patterns.md](integration-testing-patterns.md)** — writing integration tests that interact with filesystem, testing time-dependent operations, handling mtime resolution in tests
- **[mock-elimination.md](mock-elimination.md)** — refactoring tests to remove unittest.mock, replacing patch() calls with fakes, improving test maintainability
- **[monkeypatch-elimination-checklist.md](monkeypatch-elimination-checklist.md)** — migrating tests from monkeypatch to gateways, eliminating subprocess mocks, refactoring tests to use fakes
- **[rebase-conflicts.md](rebase-conflicts.md)** — fixing merge conflicts in erk tests, ErkContext API changes during rebase, env_helpers conflicts
- **[session-log-fixtures.md](session-log-fixtures.md)** — creating JSONL fixtures for session log tests, testing session plan extraction, writing integration tests for session parsing
- **[session-store-testing.md](session-store-testing.md)** — testing code that reads session data, using FakeClaudeCodeSessionStore, mocking session ID lookup
- **[submit-pipeline-tests.md](submit-pipeline-tests.md)** — adding tests for submit pipeline steps, understanding how pipeline steps are tested in isolation, working with tests/unit/cli/commands/pr/submit_pipeline/
- **[subprocess-testing.md](subprocess-testing.md)** — testing code that uses subprocess, creating fakes for process execution, avoiding subprocess mocks in tests
- **[testing.md](testing.md)** — writing tests for erk, using erk fakes, running erk test commands
- **[vitest-fake-timers-with-promises.md](vitest-fake-timers-with-promises.md)** — testing React components with setInterval or setTimeout, using Vitest fake timers with async/await code, debugging tests that hang when advancing fake timers, testing auto-refresh patterns in React
- **[vitest-jsdom-stubs.md](vitest-jsdom-stubs.md)** — writing React component tests with Vitest + jsdom, encountering "scrollIntoView is not a function" errors, setting up Vitest test environment
- **[window-mock-patterns.md](window-mock-patterns.md)** — testing erkdesk components that use window.erkdesk IPC bridge, encountering mock contamination between tests, tests passing individually but failing in CI
