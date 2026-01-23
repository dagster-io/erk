---
title: No-Changes Handling Workflow
read_when:
  - "debugging workflows that produce no changes"
  - "understanding no-changes label and detection"
  - "implementing has_changes workflow gating"
---

# No-Changes Handling Workflow

When remote implementation produces no code changes, erk handles this gracefully rather than failing the workflow. This document explains why this happens, how it's detected, and how it's handled.

## Why No-Changes Scenarios Occur

Common causes for implementation producing no changes:

| Cause              | Description                                                       |
| ------------------ | ----------------------------------------------------------------- |
| Duplicate plan     | Work was already implemented and merged to trunk                  |
| Documentation-only | Plan described documentation changes already applied              |
| Stale plan         | Codebase evolved to include the planned changes through other PRs |
| Already rebased    | Changes landed via another branch that was merged                 |

## Detection Mechanism

Detection happens in the `erk-impl.yml` workflow's "Handle implementation outcome" step:

```yaml
# Check for changes excluding .worker-impl/ and .impl/
CHANGES=$(git status --porcelain | grep -v '^\s*D.*\.worker-impl/' | grep -v '\.impl/' || true)

if [ -z "$CHANGES" ]; then
  echo "No code changes detected, handling gracefully..."
  # ...call handle-no-changes exec command
  echo "has_changes=false" >> $GITHUB_OUTPUT
else
  echo "has_changes=true" >> $GITHUB_OUTPUT
fi
```

**Key detail**: The `.worker-impl/` and `.impl/` folders are excluded from change detection since they're workflow artifacts, not implementation output.

## Handling Workflow

When no changes are detected, `erk exec handle-no-changes` is called:

```bash
erk exec handle-no-changes \
  --pr-number "$PR_NUMBER" \
  --issue-number "$ISSUE_NUMBER" \
  --behind-count "$BEHIND_COUNT" \
  --base-branch "$BASE_BRANCH" \
  --recent-commits "$RECENT_COMMITS" \
  --run-url "$WORKFLOW_RUN_URL"
```

This command:

1. **Updates PR body** with diagnostic information explaining why no changes were made
2. **Adds `no-changes` label** to the PR for easy filtering
3. **Marks PR ready for review** so users can assess the situation
4. **Adds comment to plan issue** linking to the PR

## Workflow Step Gating

The `has_changes` output variable gates subsequent workflow steps:

```yaml
- name: Submit branch with proper commit message
  if: steps.implement.outputs.implementation_success == 'true' && steps.handle_outcome.outputs.has_changes == 'true'
  # ...only runs when there are actual code changes

- name: Mark PR ready for review
  if: ... && steps.handle_outcome.outputs.has_changes == 'true'
  # ...only runs when there are actual code changes
```

This prevents attempting to commit/push when there's nothing to commit.

## Recovery Strategies

### For Users

When you see a PR with the `no-changes` label:

1. **Review recent commits** listed in the PR body to check if work was already done
2. **If work is complete**: Close both the PR and the linked plan issue
3. **If work is not complete**: Investigate why the agent produced no changes (check workflow logs)

### For Developers

When implementing no-changes handling:

1. Always gather diagnostic info (commits behind, recent commits on base)
2. Use labels for filtering (not just PR body text)
3. Link to workflow run for debugging
4. Exit with code 0 to make workflow succeed (not fail)

## Related Documentation

- [Plan Lifecycle](lifecycle.md) - Full plan lifecycle including remote implementation
- [GitHub API Rate Limits](../architecture/github-api-rate-limits.md) - API patterns used in exec commands
