---
title: HealthCheckRunner Gateway Pattern
read_when:
  - "working with health check infrastructure"
  - "modifying doctor command"
  - "adding new health checks"
  - "working with artifact allowlist"
tripwires:
  - action: "using monkeypatch to stub health check results in doctor tests"
    warning: "Use FakeHealthCheckRunner with constructor-injected results instead. The HealthCheckRunner gateway eliminates all monkeypatch in doctor tests."
  - action: "modifying artifact allowlist loading without updating both config files"
    warning: "Allowlist loads from both .erk/config.toml and .erk/config.local.toml, merging results into a frozenset."
---

# HealthCheckRunner Gateway Pattern

A simplified gateway pattern for health check result injection, replacing monkeypatch in doctor tests.

## Gateway Structure

Unlike full gateways (which have 4 files: ABC + Real + Fake + DryRun), HealthCheckRunner uses a simplified 3-file pattern because health checks are read-only — no dry-run wrapper needed.

### ABC + Real Implementation

**File:** `src/erk/core/health_checks/runner.py`

- `HealthCheckRunner` ABC with single method: `run_all(ctx, *, check_hooks: bool) -> list[CheckResult]`
- `RealHealthCheckRunner` delegates to `run_all_checks()` with lazy import to avoid circular dependencies

### Fake Implementation

**File:** `tests/fakes/health_check_runner.py`

- `FakeHealthCheckRunner` accepts `results: list[CheckResult]` at construction
- `run_all()` returns the pre-configured results (fully deterministic)

### Context Integration

The runner is an optional field on `ErkContext` with a `TYPE_CHECKING` import. The doctor command falls back to calling `run_all_checks()` directly if no runner is injected.

## Doctor Warning Display

The doctor command uses a three-way conditional for condensed subgroup display:

1. **All passed, no warnings**: Single-line summary (collapsed)
2. **All passed, has warnings**: Expand only warnings with details
3. **Any failures**: Show summary + expand only failures

Subgroups are defined in `REPO_SUBGROUPS` and `USER_SUBGROUPS` dicts mapping display names to check name sets.

## Artifact Allowlist

**File:** `src/erk/core/health_checks/managed_artifacts.py`

The allowlist loader (`managed_artifacts.py:72`) reads `[artifacts].allow_modified` from both:

- `.erk/config.toml` (shared config)
- `.erk/config.local.toml` (local overrides)

Results are merged into a `frozenset`. Locally-modified artifacts in the allowlist are treated as `up-to-date` in status evaluation, with verbose output showing `(locally-modified, allowed by config)`.

## Related Documentation

- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) — full 4-place gateway pattern
- [Erk Architecture Patterns](erk-architecture.md) — context integration patterns
