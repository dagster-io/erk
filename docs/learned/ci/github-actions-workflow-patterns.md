---
title: GitHub Actions Workflow Patterns
read_when:
  - "writing GitHub Actions workflows"
  - "debugging workflow conditions"
  - "composing step conditions"
tripwires:
  - action: "composing conditions across multiple GitHub Actions workflow steps"
    warning: "Verify each `steps.step_id.outputs.key` reference exists and matches actual step IDs."
last_audited: "2026-02-08"
audit_result: edited
---

# GitHub Actions Workflow Patterns

Cross-cutting patterns for composing conditions and coordinating multi-job workflows in erk's CI.

## Why Compound Conditions Matter in Erk

Erk's CI architecture uses **compound conditions** to coordinate 10+ parallel jobs with conditional downstream steps. A silent condition failure (typo in a step ID, wrong output key) causes the autofix job to skip when it should run, or worse, run when conditions aren't met.

The cost of silent failures:

- **Autofix skips** → developer manually fixes issues that could auto-resolve
- **Autofix runs prematurely** → pushes broken code, re-triggers CI loop
- **Jobs run unnecessarily** → waste CI minutes on draft PRs or plan reviews

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

<!-- Source: .github/workflows/ci.yml, autofix job conditions -->

See the autofix job in `.github/workflows/ci.yml:151-162` for a production example of compound conditions across multiple job outputs. The condition checks 5 different `needs.<job>.result` values, each of which must reference an actual job name.

### Output Key Mismatch

Less obvious: referencing the wrong key in a step's outputs.

```yaml
# WRONG: Key is 'skip', not 'should_skip'
- name: Run tests
  if: steps.check.outputs.should_skip != 'true' # Key is actually 'skip'
  run: pytest
```

<!-- Source: .github/workflows/ci.yml, check-submission job -->

See `.github/workflows/ci.yml:20-29` where the `check-submission` job exposes `skip` as an output. Multiple downstream jobs reference `needs.check-submission.outputs.skip` — if any job used `should_skip` instead, it would silently skip.

## Property Vocabulary: outcome vs outputs vs result

GitHub Actions has three similar-sounding properties with different semantics:

| Property  | Scope | Type   | Values                               | Use Case                            |
| --------- | ----- | ------ | ------------------------------------ | ----------------------------------- |
| `outcome` | Steps | string | success, failure, cancelled, skipped | Check if current job's step ran     |
| `outputs` | Steps | object | Custom key-value pairs               | Pass data between steps in same job |
| `result`  | Jobs  | string | success, failure, cancelled, skipped | Check if upstream job succeeded     |

**Critical distinction:** Steps in job A cannot reference `steps.*` from job B. Use `needs.<job>.outputs.*` to access outputs from upstream jobs.

<!-- Source: .github/workflows/ci.yml, autofix job -->

See `.github/workflows/ci.yml:151-162` for `needs.<job>.result` usage (job-level) vs `.github/workflows/ci.yml:217` for `steps.<step>.outputs.*` usage (step-level within the same job).

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

- Descriptive, not generic: `discover-pr` not `step1`
- Verb-noun structure: `check-submission`, `collect-failures`, `run-autofix`
- No abbreviations: `implementation` not `impl`

<!-- Source: .github/workflows/ci.yml, all step IDs -->

Browse `.github/workflows/ci.yml` for 20+ examples of step ID naming that follow this pattern.

## Multi-Job Coordination Pattern

Erk's CI uses a **fan-out → fan-in** pattern:

1. **Gate job** (`check-submission`) runs first, exposes `skip` output
2. **Parallel jobs** (`format`, `lint`, `prettier`, `ty`, `unit-tests`) all depend on gate job and check `needs.check-submission.outputs.skip`
3. **Autofix job** depends on all parallel jobs, checks their `result` values

This architecture requires:

- Gate job MUST expose outputs that downstream jobs reference
- Autofix condition MUST check `needs.<job>.result` for EVERY parallel job
- Any new parallel job MUST be added to autofix's `needs:` list and condition

<!-- Source: .github/workflows/ci.yml, jobs structure -->

See `.github/workflows/ci.yml:19-30` for the gate job, `.github/workflows/ci.yml:32-145` for parallel jobs, and `.github/workflows/ci.yml:148-398` for the autofix fan-in.

## Related Documentation

- [Autofix Job Needs](autofix-job-needs.md) - Keeping autofix job synchronized with upstream jobs
- [GitHub Actions Output Patterns](github-actions-output-patterns.md) - Multi-line outputs and GITHUB_OUTPUT usage
- [Composite Action Patterns](composite-action-patterns.md) - Reusable action setup patterns
