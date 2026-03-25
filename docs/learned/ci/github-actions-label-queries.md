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
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
---

# GitHub Actions Label Queries

## The Asymmetry Problem

GitHub Actions workflows face a fundamental asymmetry in how PR labels are accessed:

**pull_request events**: The `github.event.pull_request` context is populated, so labels are available via `github.event.pull_request.labels.*.name` at job evaluation time (before any steps run).

**push events**: The `github.event.pull_request` context does **not exist**. There is no PR context at job evaluation time, even if the push is to a branch with an open PR.

This asymmetry is architectural, not a bug. Push events are branch operations; GitHub Actions doesn't implicitly resolve "what PR is this branch associated with?" until you ask via the API.

## Why This Matters for CI Gating

Any workflow that wants to make decisions based on PR labels must handle both event types correctly:

- Users can trigger CI via **pull_request events** (opening/updating PR in GitHub UI)
- Users can trigger CI via **push events** (git push from local terminal)

If your workflow only handles pull_request events, local pushes will bypass your gating logic.

## Recommended Pattern

After the CI simplification, no active repo workflow uses step-level label queries. But if you add a push-triggered workflow that must respect PR labels, this is still the correct pattern:

1. **Use a job-level condition for pull_request events** when possible to avoid runner allocation
2. **Discover the PR number in a step** for push events
3. **Fetch labels via `gh api`**
4. **Publish a single output** that later steps consume

Example:

```yaml
- name: Discover PR
  id: discover-pr
  env:
    GH_TOKEN: ${{ github.token }}
  run: |
    if [ "${{ github.event_name }}" = "pull_request" ]; then
      echo "pr_number=${{ github.event.pull_request.number }}" >> "$GITHUB_OUTPUT"
      exit 0
    fi

    PR_NUMBER=$(gh api "repos/${{ github.repository }}/pulls" \
      --jq ".[] | select(.head.ref == \"${{ github.ref_name }}\" and .state == \"open\") | .number" \
      | head -n1)
    echo "pr_number=$PR_NUMBER" >> "$GITHUB_OUTPUT"

- name: Check label
  id: check-label
  if: steps.discover-pr.outputs.pr_number != ''
  env:
    GH_TOKEN: ${{ github.token }}
  run: |
    LABELS=$(gh api "repos/${{ github.repository }}/pulls/${{ steps.discover-pr.outputs.pr_number }}" \
      --jq '[.labels[].name] | join(\",\")')
    if printf '%s' "$LABELS" | grep -q 'skip-ci'; then
      echo "skip=true" >> "$GITHUB_OUTPUT"
    else
      echo "skip=false" >> "$GITHUB_OUTPUT"
    fi
```

## Why Not Job-Level Only?

**Q: Why not skip job-level conditions and use only step-level API queries?**

A: Job-level conditions are evaluated before runner allocation. If a pull_request event has a skip label, the job-level condition prevents GitHub from even starting a runner, saving CI minutes and reducing queue pressure.

Step-level queries require a runner to be allocated, checkout to complete, and API calls to execute. This wastes resources for cases that could be rejected earlier.

The combined pattern uses the fast path when available (job-level for pull_request) and falls back to the required path when necessary (step-level for push).

## API Query Pattern

For push events, PR discovery is a two-step process:

1. **Find PR number**: `gh api repos/{repo}/pulls --jq ".[] | select(.head.ref == \"{branch}\" and .state == \"open\") | .number"`
2. **Fetch labels**: `gh api repos/{repo}/pulls/{pr_number} --jq '[.labels[].name] | join(",")'`

Use `gh api` instead of `gh pr view` because the latter requires being in a repository checkout with the PR branch, while `gh api` works from any checkout state.

## Anti-Pattern: Job-Level Push Event Checks

**WRONG:**

```yaml
if: |
  github.event_name == 'push' &&
  !contains(github.event.pull_request.labels.*.name, 'skip-ci')
```

This condition will always evaluate to true for push events because `github.event.pull_request` is null. The `contains()` function returns false when the array is empty/null, so the negation becomes true.

The job or step will run even when the PR has the label, bypassing your gating logic.

## Related Patterns

- [Workflow Gating Patterns](workflow-gating-patterns.md) - Choosing the right gating layer
- [CI Tripwires](tripwires.md) - All CI-related tripwires
