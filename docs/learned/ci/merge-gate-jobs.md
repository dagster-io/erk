---
title: Merge Gate Jobs
read_when:
  - "adding a CI job that blocks merging bad content"
  - "working with no-impl-context CI job"
  - "understanding CI job skip conditions for draft PRs"
tripwires:
  - action: "adding a merge gate job with dependencies on other CI jobs"
    warning: "Merge gate jobs run independently (no 'needs:' dependencies). They should be fast, standalone checks. See merge-gate-jobs.md."
---

# Merge Gate Jobs

Independent CI jobs that block merging problematic content into the main branch.

## Pattern

Merge gate jobs are lightweight CI jobs that:

1. Run independently — no `needs:` dependencies on other jobs
2. Have consistent skip conditions — skip on draft PRs and `erk-plan-review` labeled PRs
3. Provide clear error messages with remediation steps
4. Complete quickly (5-minute timeout)

## `no-impl-context` Job

<!-- Source: .github/workflows/ci.yml:30-42 -->

Prevents `.erk/impl-context/` directories from being merged. These directories are used during plan implementation and must be cleaned up before merge.

```yaml
no-impl-context:
  if: github.event.pull_request.draft != true && !contains(github.event.pull_request.labels.*.name, 'erk-plan-review')
  runs-on: ubuntu-latest
  timeout-minutes: 5
  steps:
    - uses: actions/checkout@v4
    - name: Ensure .erk/impl-context/ is not in tree
      run: |
        if [ -d ".erk/impl-context" ]; then
          echo "::error::.erk/impl-context/ must be removed before merging. Run: git rm -rf .erk/impl-context/ && git commit && git push"
          exit 1
        fi
```

### Skip Conditions

Both conditions must be false for the job to run:

- `github.event.pull_request.draft != true` — skips draft PRs (plan PRs are always draft)
- `!contains(github.event.pull_request.labels.*.name, 'erk-plan-review')` — skips plan review PRs

### Note on Branch Protection

The `no-impl-context` job runs on all PRs meeting the skip criteria, but branch protection rules may not currently require it to pass before merging. The job serves as a visible warning in the CI status checks.

## Adding New Merge Gate Jobs

Follow the same pattern:

1. No `needs:` — run independently
2. Same `if:` condition for draft/plan-review skip
3. Clear `::error::` message with remediation command
4. 5-minute timeout

## Related Documentation

- [Planning Workflow](../planning/) — context on `.erk/impl-context/` lifecycle
