---
title: GitHub Actions Label Queries
read_when:
  - "checking PR labels in GitHub Actions workflows"
  - "working with push event workflows"
  - "implementing CI gating based on PR labels"
tripwires:
  - score: 6
    action: "Label checks in push event workflows"
    warning: "Job-level label access via github.event.pull_request.labels is ONLY available in pull_request events, NOT push events. For push events, you must use step-level GitHub API queries with gh cli or REST API."
    context: "The asymmetry exists because push events don't have github.event.pull_request in their context. Defense-in-depth: Keep job-level checks for pull_request events (fast path), add step-level API queries for push events (required path)."
---

# GitHub Actions Label Queries

## Problem: Push Event Label Asymmetry

GitHub Actions workflows triggered by push events **cannot** access PR labels via `github.event.pull_request.labels` because the `pull_request` context is not available for push events.

This creates an asymmetry in CI gating patterns:

- **pull_request events**: Can use job-level label checks via `github.event.pull_request.labels.*.name`
- **push events**: Must use step-level API queries to fetch labels

## Solution: Step-Level API Query Pattern

For workflows that run on both pull_request and push events, use a defense-in-depth approach:

1. **Job-level condition**: Check labels for pull_request events (fast path, prevents job from running at all)
2. **Step-level API query**: Check labels for push events (required for push event support)

### Implementation Pattern

From `.github/workflows/ci.yml` (autofix job):

```yaml
autofix:
  if: |
    always() &&
    github.ref_name != 'master' &&
    (github.event_name == 'pull_request' || github.event_name == 'push') &&
    (github.event_name != 'pull_request' || !contains(github.event.pull_request.labels.*.name, 'erk-plan-review')) &&
    (needs.format.result == 'failure' || ...)
  runs-on: ubuntu-latest
  steps:
    - name: Discover PR
      id: discover-pr
      env:
        GH_TOKEN: ${{ github.token }}
      run: |
        if [ "${{ github.event_name }}" = "pull_request" ]; then
          echo "has_pr=true" >> $GITHUB_OUTPUT
          echo "pr_number=${{ github.event.pull_request.number }}" >> $GITHUB_OUTPUT
        else
          # For push events, discover PR number via gh pr list
          pr_number=$(gh pr list --head "${{ github.ref_name }}" --state open --json number --jq '.[0].number')
          if [ -n "$pr_number" ]; then
            echo "has_pr=true" >> $GITHUB_OUTPUT
            echo "pr_number=$pr_number" >> $GITHUB_OUTPUT
          else
            echo "has_pr=false" >> $GITHUB_OUTPUT
          fi
        fi

    - name: Check erk-plan-review label
      id: check-label
      if: steps.discover-pr.outputs.has_pr == 'true' && steps.pr.outputs.is_fork != 'true'
      env:
        GH_TOKEN: ${{ github.token }}
      run: |
        labels=$(gh api repos/${{ github.repository }}/pulls/${{ steps.discover-pr.outputs.pr_number }} --jq '[.labels[].name] | join(",")')
        if echo "$labels" | grep -q "erk-plan-review"; then
          echo "PR has erk-plan-review label, skipping autofix"
          echo "has_plan_review_label=true" >> $GITHUB_OUTPUT
        else
          echo "has_plan_review_label=false" >> $GITHUB_OUTPUT
        fi

    - name: Determine if autofix should run
      id: should-autofix
      run: |
        if [[ "${{ steps.discover-pr.outputs.has_pr }}" == "true" && \
              "${{ steps.pr.outputs.is_fork }}" != "true" && \
              "${{ steps.check-label.outputs.has_plan_review_label }}" != "true" && \
              "${{ steps.check.outputs.has_impl_folder }}" != "true" ]]; then
          echo "run=true" >> "$GITHUB_OUTPUT"
        else
          echo "run=false" >> "$GITHUB_OUTPUT"
        fi

    - uses: actions/setup-python@v5
      if: steps.should-autofix.outputs.run == 'true'
      # ... rest of autofix steps
```

## Skip Condition Consolidation

The `should-autofix` step consolidates all skip conditions into a single boolean output:

- **has_pr**: Must have an open PR for the branch
- **is_fork**: Skip fork PRs for security
- **has_plan_review_label**: Skip PRs with erk-plan-review label (manual review only)
- **has_impl_folder**: Skip PRs with .impl/ folder (agent-generated code)

All subsequent steps check `steps.should-autofix.outputs.run == 'true'` instead of repeating the complex condition.

## Defense-in-Depth Rationale

Why keep both job-level and step-level checks?

- **Job-level condition** (pull_request events only): Prevents job from running at all, saving CI minutes
- **Step-level API query** (all events): Required for push events, also serves as safety net for pull_request events

This pattern ensures label-based gating works correctly regardless of trigger event while minimizing unnecessary CI execution.

## Related Patterns

- [Workflow Gating Patterns](workflow-gating-patterns.md) - Autofix safety pattern
- [CI Tripwires](tripwires.md) - All CI-related tripwires
