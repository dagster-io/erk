# Real Implementation Tests

## Purpose

Tests for Real\* gateway implementations (RealGit, RealGraphite, RealGtKit, etc.) that verify command construction and output parsing by mocking subprocess calls.

These are distinct from integration tests (`tests/integration/`) which use actual external tools.

## When to Add Tests Here

- Testing a Real\* gateway implementation's command construction
- Testing subprocess output parsing logic
- Verifying error handling for external tool failures

## What Doesn't Go Here

- Tests using fakes (go in `tests/commands/` or `tests/core/`)
- Tests calling real external tools (go in `tests/integration/`)
- Tests of fake implementations (go in `tests/unit/fakes/`)
