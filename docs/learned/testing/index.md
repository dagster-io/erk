<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Testing Documentation

- **[cascading-import-cleanup.md](cascading-import-cleanup.md)** — removing modules from codebase, import errors after module deletion, cleaning up removed functionality
- **[cli-test-error-assertions.md](cli-test-error-assertions.md)** — writing CLI tests with error assertions, testing error messages in Click commands, asserting on CLI output
- **[cli-testing.md](cli-testing.md)** — writing tests for erk CLI commands, using ErkContext.for_test(), testing Click commands with context
- **[exec-script-testing.md](exec-script-testing.md)** — testing exec CLI commands, writing integration tests for scripts, debugging 'Context not initialized' errors in tests, debugging flaky tests in parallel execution
- **[import-conflict-resolution.md](import-conflict-resolution.md)** — resolving merge conflicts during rebase, fixing import conflicts after consolidation, rebasing after shared module changes
- **[integration-test-speed.md](integration-test-speed.md)** — integration test is slow, test takes too long, pytest --durations shows slow test
- **[integration-testing-patterns.md](integration-testing-patterns.md)** — writing integration tests that interact with filesystem, testing time-dependent operations, handling mtime resolution in tests
- **[mock-elimination.md](mock-elimination.md)** — refactoring tests to remove unittest.mock, replacing patch() calls with fakes, improving test maintainability
- **[mutation-tracking-patterns.md](mutation-tracking-patterns.md)** — asserting on fake gateway mutations, handling mutation tracking tuple format changes, testing BranchManager with explicit branch_ops
- **[rebase-conflicts.md](rebase-conflicts.md)** — fixing merge conflicts in erk tests, ErkContext API changes during rebase, env_helpers conflicts
- **[session-log-fixtures.md](session-log-fixtures.md)** — creating JSONL fixtures for session log tests, testing session plan extraction, writing integration tests for session parsing
- **[session-store-testing.md](session-store-testing.md)** — testing code that reads session data, using FakeClaudeCodeSessionStore, mocking session ID lookup
- **[subprocess-testing.md](subprocess-testing.md)** — testing code that uses subprocess, creating fakes for process execution, avoiding subprocess mocks in tests
- **[testing.md](testing.md)** — writing tests for erk, using erk fakes, running erk test commands
