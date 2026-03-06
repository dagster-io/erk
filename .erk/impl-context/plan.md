# Restore Review Workflow Boundary Between Repo CI and Shipped Capabilities

## Why

The current repository configuration mixes two different concerns inside one workflow graph:

- repo-local CI responsibilities such as formatting, docs sync, linting, tests, and CI failure summarization
- shipped review-system responsibilities that are installed into external repositories as capabilities

That coupling makes `ci.yml` harder to reason about, forces repo-specific coordination logic onto review execution, and has allowed the capability layer, bundling rules, tests, and docs to drift out of sync.

## Investigation Findings

- `.github/workflows/ci.yml` currently owns both repo validation and convention-based review execution via `discover-reviews` and `review`.
- `src/erk/capabilities/code_reviews_system.py` and `src/erk/core/capabilities/review_capability.py` treat `.github/workflows/code-reviews.yml` as the standalone source of truth for the shipped review system.
- `tests/unit/core/capabilities/test_code_reviews_system.py` and `tests/unit/core/capabilities/test_review_capability.py` also expect the standalone `code-reviews.yml` boundary.
- `docs/learned/ci/convention-based-reviews.md` and `docs/learned/ci/automated-review-system.md` describe a separate `code-reviews.yml` workflow, while the repo currently inlines review orchestration into `ci.yml`.
- `pyproject.toml` force-includes shipped workflow capabilities such as `learn.yml`, `plan-implement.yml`, `pr-address.yml`, and `pr-rebase.yml`, but does not currently bundle `code-reviews.yml` even though the capability layer expects it.
- `src/erk/artifacts/sync.py` still contains legacy review-workflow packaging logic for `dignified-python-review.yml`, which does not match the capability model centered on the unified review system.
- `.github/workflows/README.md` still references older per-review workflow names, which adds to the product-vs-repo ambiguity.

## Goals

- Restore a clean boundary between repo-local CI and shipped review capabilities.
- Make `code-reviews.yml` the canonical entrypoint for convention-based review capabilities again.
- Keep `fix-formatting` and all validation/test behavior in repo-local CI.
- Reconcile capability code, artifact bundling, tests, and docs so they all describe and validate the same architecture.
- Reduce cognitive load in `ci.yml` after reviews are no longer embedded in it.

## Non-Goals

- Redesign individual review definitions in `.erk/reviews/`.
- Change review prompt content or review taxonomy.
- Rework non-review shipped workflows such as `learn.yml`, `plan-implement.yml`, `pr-address.yml`, or `pr-rebase.yml`.
- Enable the disabled Claude CI autofix path as part of this change.

## Files And Surfaces To Reconcile

- `.github/workflows/ci.yml`
- `.github/workflows/code-reviews.yml`
- `src/erk/capabilities/code_reviews_system.py`
- `src/erk/core/capabilities/review_capability.py`
- `src/erk/artifacts/sync.py`
- `src/erk/artifacts/artifact_health.py`
- `pyproject.toml`
- `.github/workflows/README.md`
- `docs/learned/ci/convention-based-reviews.md`
- `docs/learned/ci/automated-review-system.md`
- `docs/learned/ci/job-ordering-strategy.md`
- `docs/learned/ci/workflow-gating-patterns.md`
- `tests/unit/core/capabilities/test_code_reviews_system.py`
- `tests/unit/core/capabilities/test_review_capability.py`
- `tests/artifacts/test_sync.py`

## Implementation Steps

### 1. Restore The Standalone Review Workflow Boundary

- Create `.github/workflows/code-reviews.yml` as the canonical review-system workflow using the current `discover-reviews` and `review` behavior that now lives inside `ci.yml`.
- Preserve the current review guards and ergonomics:
  - skip drafts
  - skip `erk-plan-review` PRs
  - respect `CLAUDE_ENABLED`
  - preserve the local-review marker fast path
- Keep review workflow permissions scoped to review needs rather than inheriting repo-CI write permissions.
- Remove `discover-reviews` and `review` from `ci.yml` in the same change so the migration does not produce duplicate review runs or duplicate review comments.

Verification:

- A non-draft PR with matching review definitions triggers exactly one review workflow.
- Review comments are produced by `code-reviews.yml`, not by `ci.yml`.
- `ci.yml` no longer references review discovery or review execution jobs.

### 2. Reconcile The Capability Layer And Bundle Manifest

- Make the capability system, bundled artifacts, and repo source tree agree that `code-reviews.yml` is the review-system entrypoint.
- Update `src/erk/capabilities/code_reviews_system.py` and `src/erk/core/capabilities/review_capability.py` only as needed to align with the restored workflow source of truth.
- Add the shipped review workflow to `pyproject.toml` force-includes so wheel installs and editable installs expose the same review-system artifact.
- Audit artifact ownership and health reporting so `code-reviews-system` manages the workflow and its required actions consistently.
- Decide what to do with legacy per-review workflow sync logic in `src/erk/artifacts/sync.py`:
  - remove it if it is obsolete
  - or preserve it only if there is a documented compatibility requirement

Verification:

- `code-reviews-system` installation expects and installs `.github/workflows/code-reviews.yml`.
- Review-definition capabilities still preflight on the standalone review workflow.
- Bundled artifacts for review infrastructure are present in wheel metadata and editable installs resolve to the same source-of-truth files.

### 3. Simplify Repo-Local CI After The Split

- Keep repo-local CI focused on `check-submission`, `fix-formatting`, validation jobs, and `ci-summarize`.
- Treat `fix-formatting` as the only mutating boundary in repo CI.
- Remove the disabled `autofix` job and any workflow-wide permissions that only existed to support dead or moved behavior.
- Keep any `pushed` coordination local to repo validation rather than leaking it into shipped review behavior.
- If YAML duplication remains a problem after the boundary is restored, extract shared validation setup into composite actions or a repo-internal reusable workflow that is not treated as a shipped capability surface.

Verification:

- `ci.yml` contains repo validation and summarization only.
- Review-specific gating is gone from repo CI.
- Workflow permissions are reduced to the minimum required by active repo-CI behavior.

### 4. Repair Documentation And Regression Coverage

- Update learned docs so they match the restored boundary between repo CI and shipped review capabilities.
- Update `.github/workflows/README.md` so its workflow inventory reflects the current shipped and repo-local workflows.
- Update unit tests covering `CodeReviewsSystemCapability` and `ReviewCapability` to validate the restored workflow boundary.
- Update artifact-sync tests to cover the shipped review workflow and to remove assertions tied to obsolete per-review workflow packaging, if that path is removed.
- Add a regression test that protects the key product boundary: review capabilities preflight on `code-reviews.yml`, not on `ci.yml`.

Verification:

- Docs and tests describe the same workflow topology the code implements.
- No tests or docs refer to obsolete per-review workflow names unless explicitly retained for compatibility.

## Acceptance Criteria

- `code-reviews-system` installs a standalone `.github/workflows/code-reviews.yml` plus the actions it needs.
- Review-definition capabilities continue to depend on the standalone review workflow rather than repo-local CI.
- `.github/workflows/ci.yml` no longer owns review discovery or review execution.
- Repo-local CI still handles formatting, docs sync/checks, linting, typing, tests, and CI failure summarization.
- The wheel bundle manifest includes the shipped review workflow so external projects receive the same review-system infrastructure the capability layer expects.
- Artifact sync and artifact health checks agree on ownership for the review workflow and related actions.
- The repo’s learned docs and workflow README no longer contradict the implemented architecture.

## Validation Plan

- Run targeted capability and artifact tests covering the review system.
- Run workflow-focused validation for the moved review logic and the simplified repo CI.
- Run a repo-level CI sanity pass after the refactor to ensure format, docs, lint, type, and test jobs still execute in the intended order.
- Verify the review capability flow manually or with tests in a temporary repository setup:
  - install `code-reviews-system`
  - install one or more review-definition capabilities
  - confirm the standalone review workflow is the execution path

## Risks And Decision Points

- The migration must avoid any window where both `ci.yml` and `code-reviews.yml` run reviews, or PRs will receive duplicate review output.
- Legacy per-review workflow packaging may still matter to external users; if so, treat compatibility as an explicit migration decision rather than an accidental leftover.
- Reusable workflows can reduce YAML duplication, but they require explicit input forwarding and can become another maintenance surface. Prefer composite actions unless the reusable-workflow boundary clearly pays for itself.
- If there are external consumers relying on the current inlined review behavior in `ci.yml`, document the migration and verify that capability installation continues to produce the expected workflow files.
