---
title: Fake Mutation Tracking
read_when:
  - "writing a new fake gateway implementation"
  - "adding mutation tracking to test doubles"
  - "asserting on gateway method calls in tests"
tripwires:
  - action: "using mutable list fields directly for mutation tracking in fakes"
    warning: "Expose mutation tracking via @property returning tuple or .copy(). Internal lists should be private. See fake-mutation-tracking.md."
---

# Fake Mutation Tracking

Fake gateways track mutations via private list fields exposed as immutable properties. This is a cross-cutting pattern used consistently across erk's test infrastructure.

## Pattern

Internal state uses `list[tuple[...]]` for append operations during test execution. Public access is via `@property` methods that return immutable copies for assertions.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github_admin/fake.py, FakeGitHubAdmin._set_secret_calls and FakeGitHubAdmin.set_secret_calls -->

See `FakeGitHubAdmin._set_secret_calls` (private mutable list) and `set_secret_calls` property (returns immutable tuple) in `packages/erk-shared/src/erk_shared/gateway/github_admin/fake.py`.

## Examples

### FakeGitHubAdmin

`packages/erk-shared/src/erk_shared/gateway/github_admin/fake.py`:

- `set_secret_calls` — `tuple[tuple[str, str], ...]` (name, value)
- `delete_secret_calls` — `tuple[str, ...]` (secret names)
- `set_permission_calls` — `tuple[tuple[Path, bool], ...]`

### FakeGitHub

`packages/erk-shared/src/erk_shared/gateway/github/fake.py` tracks many mutation types:

- `created_prs` — `list[tuple[str, str, str, str | None, bool]]` (branch, title, body, base, is_draft)
- `created_gists` — `list[tuple[str, str, str, bool]]`
- `updated_pr_bodies` — `list[tuple[int, str]]`
- `added_labels` — `list[tuple[int, str]]`
- `triggered_workflows` — `list[tuple[str, dict[str, str]]]`

Properties return raw mutable lists directly (no defensive copying). Docstrings indicate "read-only access" but this is by convention only.

### FakeGit

`packages/erk-shared/src/erk_shared/gateway/git/fake.py`:

- `created_branches` — `list[tuple[Path, str, str, bool]]` (cwd, name, start_point, force)
- `checked_out_branches` — `list[tuple[Path, str]]` (cwd, branch_name)

Properties return `.copy()`.

## Convention

- Use `tuple[...]` types for the record structure (positional fields)
- Private `list` field with `_` prefix for internal mutation
- Public `@property` returning `tuple(self._field)` or `self._field.copy()`
- Assertions check property contents for expected calls

## Related Topics

- [GitHub Admin Gateway](github-admin-gateway.md) - Example implementation
- [Gateway ABC Implementation](gateway-abc-implementation.md) - Full 5-place pattern
