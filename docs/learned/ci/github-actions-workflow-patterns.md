---
title: GitHub Actions Workflow Patterns
read_when:
  - "writing GitHub Actions workflows"
  - "debugging workflow conditions"
  - "composing step conditions"
tripwires:
  - action: "composing conditions across multiple GitHub Actions workflow steps"
    warning: "Verify each `steps.step_id.outputs.key` reference exists and matches actual step IDs."
  - action: "creating or modifying a reusable GitHub Actions workflow (workflow_call) that depends on ERK_PLAN_BACKEND or other env vars"
    warning: "Reusable workflow input forwarding: GitHub Actions reusable workflows (via workflow_call) do NOT inherit environment variables from the caller workflow. Declare ERK_PLAN_BACKEND (and any other required env vars) as explicit inputs in the reusable workflow, and pass them explicitly from the caller workflow. Ambient env vars are NOT forwarded automatically."
    score: 8
last_audited: "2026-02-16 14:20 PT"
audit_result: edited
---

# GitHub Actions Workflow Patterns

Cross-cutting patterns for composing conditions and coordinating multi-job workflows in erk's GitHub Actions setup.

## Why Compound Conditions Matter in Erk

Erk's workflow architecture uses compound conditions to coordinate repo-local validation, a mutating `fix-formatting` boundary, and a separate review matrix workflow. A silent condition failure (typo in a step ID, wrong output key) causes stale validation, skipped summaries, or unnecessary runner allocation.

The cost of silent failures:

- **Validation runs on stale code** → jobs execute before the formatter rerun takes over
- **Summaries skip unexpectedly** → CI failures lose their synthesized explanation
- **Review discovery runs unnecessarily** → advisory workflows burn CI minutes on drafts or locally-reviewed commits

## Compound Condition Failure Modes

### Step ID Mismatch

The most common silent failure: referencing a step ID that doesn't exist.

```yaml
# WRONG: Step ID doesn't exist
- name: Deploy
  if: steps.build.outcome == 'success' # No step with id: build
  run: deploy
```

GitHub Actions silently evaluates the missing step as undefined, making the condition false. No error is raised.

<!-- Source: .github/workflows/ci.yml, ci-summarize job -->

See the `ci-summarize` job in `.github/workflows/ci.yml` for a production example of compound conditions across multiple upstream job results.

### Output Key Mismatch

Less obvious: referencing the wrong key in a step's outputs.

```yaml
# WRONG: Key is 'skip', not 'should_skip'
- name: Run tests
  if: steps.check.outputs.should_skip != 'true' # Key is actually 'skip'
  run: pytest
```

<!-- Source: .github/workflows/ci.yml, check-submission job -->
<!-- Source: .github/workflows/ci.yml, fix-formatting job -->

See `.github/workflows/ci.yml` where `check-submission` exposes `skip` and `fix-formatting` exposes `pushed`. Multiple downstream jobs reference both outputs — if any job used the wrong key, it would silently skip or validate the wrong commit.

### Missing Step ID

```yaml
# WRONG: No id, can't reference this step
- name: Run tests
  run: npm test

- name: Deploy if tests pass
  if: steps.run-tests.outcome == 'success' # Always false!
  run: deploy
```

### Typo in Step Reference

```yaml
- name: Build
  id: build-step

- name: Deploy
  if: steps.build.outcome == 'success' # Wrong! Should be 'build-step'
  run: deploy
```

### Wrong Output Key

```yaml
- name: Check
  id: check
  run: echo "result=pass" >> $GITHUB_OUTPUT

- name: Use result
  if: steps.check.outputs.outcome == 'pass' # Wrong! Key is 'result'
  run: echo "passed"
```

## Property Vocabulary: outcome vs outputs vs result

GitHub Actions has three similar-sounding properties with different semantics:

| Property  | Scope | Type   | Values                               | Use Case                            |
| --------- | ----- | ------ | ------------------------------------ | ----------------------------------- |
| `outcome` | Steps | string | success, failure, cancelled, skipped | Check if current job's step ran     |
| `outputs` | Steps | object | Custom key-value pairs               | Pass data between steps in same job |
| `result`  | Jobs  | string | success, failure, cancelled, skipped | Check if upstream job succeeded     |

**Critical distinction:** Steps in job A cannot reference `steps.*` from job B. Use `needs.<job>.outputs.*` to access outputs from upstream jobs.

<!-- Source: .github/workflows/ci.yml, ci-summarize job -->
<!-- Source: .github/workflows/code-reviews.yml, discover job -->

See `ci-summarize` in `.github/workflows/ci.yml` for `needs.<job>.result` usage and `discover` in `.github/workflows/code-reviews.yml` for `steps.<step>.outputs.*` usage within a job.

## Step Condition Patterns

### Robust Conditional with Output Check

```yaml
- name: Build
  id: build
  run: |
    npm run build
    echo "artifact_path=dist/" >> $GITHUB_OUTPUT

- name: Deploy
  if: |
    steps.build.outcome == 'success' &&
    steps.build.outputs.artifact_path != ''
  run: deploy ${{ steps.build.outputs.artifact_path }}
```

### Complete Step Pattern

```yaml
- name: Human-readable description
  id: machine-readable-id
  run: |
    # Do work
    echo "key=value" >> $GITHUB_OUTPUT
  continue-on-error: true # If step failure shouldn't fail job
```

### When to Add Step IDs

Add `id:` to steps that:

- Output values other steps need
- Are referenced in conditions
- Might fail and need status checks

## Validation Discipline for Erk Workflows

Before adding compound conditions to erk's workflows:

1. **Grep for the step ID** — Confirm `id: <name>` exists in the workflow
2. **Grep for the output key** — Find `echo "<key>=<value>" >> $GITHUB_OUTPUT` in the step
3. **Check scope** — Steps reference other steps, jobs reference other jobs via `needs`
4. **Test the negative case** — What happens if the step is skipped? Use `always()` or `if: always() &&` to ensure steps run even when upstream fails

### Anti-Pattern: Silently Skipping Cleanup

```yaml
# WRONG: Cleanup never runs if tests fail
- name: Run tests
  id: test
  run: pytest

- name: Cleanup
  if: steps.test.outcome == 'success' # Skips on failure!
  run: cleanup.sh
```

If tests fail, cleanup never runs. Use `if: always()` to ensure cleanup happens regardless of test outcome.

## Step ID Naming in Erk

Erk's workflows use `kebab-case` for step IDs to match the broader naming convention (commands, skills, hooks all use kebab-case).

**Pattern:**

- Descriptive, not generic: `check-local-review` not `step1`
- Verb-noun structure: `check-submission`, `fix-formatting`, `discover`
- No abbreviations: `implementation` not `impl`

<!-- Source: .github/workflows/ci.yml, all step IDs -->

Browse `.github/workflows/ci.yml` for 20+ examples of step ID naming that follow this pattern.

## Multi-Job Coordination Pattern

Erk now uses two distinct orchestration shapes:

### Repo CI (`ci.yml`)

1. **Gate job** (`check-submission`) runs first and exposes `skip`
2. **Mutating boundary** (`fix-formatting`) runs next and exposes `pushed`
3. **Parallel validation jobs** depend on both and skip when `pushed == 'true'`
4. **Failure fan-in** (`ci-summarize`) depends on all validation jobs and inspects `needs.<job>.result`

This architecture requires:

- Validation jobs MUST depend on both `check-submission` and `fix-formatting`
- Validation jobs MUST use the correct `skip` and `pushed` outputs
- Any new validation job that should appear in summaries MUST be added to `ci-summarize.needs`

### Review Workflow (`code-reviews.yml`)

1. **Discover job** computes a matrix and `has_reviews`
2. **Review job** fans out across the matrix

This architecture requires:

- Discovery step IDs and output keys MUST stay in sync with job outputs
- Review execution belongs in `code-reviews.yml`, not `ci.yml`

## Related Documentation

- [CI Job Ordering Strategy](job-ordering-strategy.md) - Repo CI job ordering and `fix-formatting` gating
- [Convention-Based Code Reviews](convention-based-reviews.md) - Separate review workflow architecture
- [GitHub Actions Output Patterns](github-actions-output-patterns.md) - Multi-line outputs and GITHUB_OUTPUT usage
- [Composite Action Patterns](composite-action-patterns.md) - Reusable action setup patterns
