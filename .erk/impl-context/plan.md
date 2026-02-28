# Plan: Run fix-formatting before all other CI jobs

## Context

Currently all CI jobs (`format`, `lint`, `fix-formatting`, `docs-check`, `ty`, `unit-tests`, `integration-tests`, `erkbot-tests`) run in parallel after `check-submission`. This means when code needs formatting fixes, the `format` job fails immediately while `fix-formatting` is simultaneously auto-fixing and pushing. The user sees a confusing red X that gets superseded when the new CI run triggers.

By making `fix-formatting` run first, we get:
- If formatting fixes are needed: `fix-formatting` pushes a commit, the workflow is cancelled (`cancel-in-progress: true`), and a clean CI run starts on the fixed code — no wasted compute on doomed jobs
- If no fixes needed: other jobs proceed immediately after `fix-formatting` completes

## Changes

**File:** `.github/workflows/ci.yml`

Add `fix-formatting` to the `needs` list of every parallel job so they wait for it:

| Job | Current `needs` | New `needs` |
|-----|----------------|-------------|
| `format` | `check-submission` | `[check-submission, fix-formatting]` |
| `lint` | `check-submission` | `[check-submission, fix-formatting]` |
| `docs-check` | `check-submission` | `[check-submission, fix-formatting]` |
| `ty` | `check-submission` | `[check-submission, fix-formatting]` |
| `unit-tests` | `check-submission` | `[check-submission, fix-formatting]` |
| `integration-tests` | `check-submission` | `[check-submission, fix-formatting]` |
| `erkbot-tests` | `check-submission` | `[check-submission, fix-formatting]` |

`fix-formatting` itself keeps `needs: check-submission` only (no change).

The `autofix` and `ci-summarize` jobs don't need changes since they already transitively depend on `fix-formatting`.

## Verification

- Push a PR with unformatted code: `fix-formatting` should run first, push a fix, and cancel the run before other jobs start
- Push a PR with clean code: `fix-formatting` completes quickly, then all other jobs run in parallel as before
