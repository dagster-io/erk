# Test GitHub Actions Workflows

Test changes to erk's GitHub Actions workflows before merging.

## Overview

When modifying workflow files like `.github/workflows/erk-impl.yml`, you need to test the actual workflow execution, not just the YAML syntax. This guide shows how to use `erk admin test-erk-impl-gh-workflow` to automate this process.

## Prerequisites

- Your workflow changes committed to a branch
- GitHub CLI (`gh`) authenticated
- Push access to the repository

## Quick Start

```bash
# Test erk-impl workflow from your current branch
erk admin test-erk-impl-gh-workflow

# Use an existing issue (avoids creating a new one)
erk admin test-erk-impl-gh-workflow --issue 12345

# Watch the run in real-time
erk admin test-erk-impl-gh-workflow --watch
```

## What the Command Does

1. **Pushes your branch** - Ensures your workflow changes are on remote
2. **Creates a test issue** - Or uses an existing one with `--issue`
3. **Creates a test branch** - Pushes `master` to `test-workflow-{timestamp}`
4. **Creates a draft PR** - Required by the workflow's `pr_number` input
5. **Triggers the workflow** - Uses `--ref` to run YOUR version of the YAML
6. **Returns the run URL** - So you can monitor the execution

## Understanding --ref

The key insight is that `gh workflow run --ref <branch>` runs the workflow file **from that branch**, not just with different inputs. This means:

- Changes to workflow steps, jobs, and scripts take effect
- You're testing the actual modified workflow, not the one on `master`

## Example Output

```
Ensuring branch 'my-workflow-fix' exists on remote...
✓ Branch 'my-workflow-fix' pushed to origin
✓ Created test issue #4358
Creating test branch 'test-workflow-abc123'...
✓ Test branch 'test-workflow-abc123' created
✓ Draft PR #4359 created
Triggering erk-impl workflow from 'my-workflow-fix'...

Workflow triggered successfully!

Run URL: https://github.com/dagster-io/erk/actions/runs/123456789
Test branch: test-workflow-abc123
Draft PR: https://github.com/dagster-io/erk/pull/4359
```

## Cleanup After Testing

The command creates test artifacts that you should clean up:

```bash
# Delete the test branch
git push origin --delete test-workflow-abc123

# Close the draft PR (use the PR number from output)
gh pr close 4359

# Optionally close the test issue if you created one
gh issue close 4358
```

## When to Use This

- **Modifying erk-impl.yml** - Test before merging changes
- **Debugging workflow failures** - Reproduce issues with your fixes
- **Testing new workflow inputs** - Verify parameter handling
- **Developing new workflows** - Iterate on workflow logic

## Manual Alternative

For more control, you can trigger workflows manually:

```bash
# 1. Push your branch
git push origin HEAD

# 2. Create test infrastructure
git push origin master:test-branch
gh pr create --head test-branch --base master --draft --title "Test"

# 3. Trigger with --ref pointing to YOUR branch
gh workflow run erk-impl.yml \
  --ref your-branch-with-workflow-changes \
  -f issue_number=12345 \
  -f submitted_by=your-username \
  -f distinct_id=test123 \
  -f issue_title="Test" \
  -f branch_name=test-branch \
  -f pr_number=PR_NUMBER \
  -f base_branch=master
```

## See Also

- [Remote Execution](remote-execution.md) - How remote implementation works
- [The Workflow](../topics/the-workflow.md) - Overview of erk's workflow
