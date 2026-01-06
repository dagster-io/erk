---
title: Testing Workflow Changes
read_when:
  - Testing changes to GitHub Actions workflows
  - Modifying erk-impl.yml workflow
  - Debugging workflow dispatch issues
---

# Testing Workflow Changes

How to test changes to GitHub Actions workflows (like `erk-impl.yml`).

## Using `erk admin test-erk-impl-gh-workflow`

When modifying workflow files, use this command to test from your branch:

```bash
# Test erk-impl workflow from current branch
erk admin test-erk-impl-gh-workflow

# Use an existing issue
erk admin test-erk-impl-gh-workflow --issue 19878

# Watch the run
erk admin test-erk-impl-gh-workflow --watch
```

## What It Does

1. Pushes current branch to remote (if needed)
2. Creates a test branch for implementation (pushes `master` to `test-workflow-{timestamp}`)
3. Creates a draft PR (workflow requires `pr_number`)
4. Triggers the workflow with `--ref` set to your branch
5. Outputs the run URL

## Why This Is Needed

Testing `erk-impl.yml` changes is tedious because:

1. **Many parameters**: The workflow requires `issue_number`, `submitted_by`, `distinct_id`, `issue_title`, `branch_name`, `pr_number`, and `base_branch`
2. **Branch must exist on remote**: The `--ref` flag requires the branch to be pushed
3. **PR must exist**: `pr_number=0` causes failures in the workflow
4. **Need to test YOUR branch**: You must use `--ref {your-branch}` to test workflow file changes (not just input changes)

## Manual Approach

If you need more control:

```bash
# 1. Push your branch
git push origin HEAD

# 2. Create test branch
git push origin master:test-branch-name

# 3. Create draft PR
gh pr create --head test-branch-name --base master --draft --title "Test"

# 4. Trigger workflow (--ref runs the YAML from your-branch)
gh workflow run erk-impl.yml \
  --ref your-branch \
  -f issue_number=ISSUE \
  -f submitted_by=USERNAME \
  -f distinct_id=$(date +%s | base36) \
  -f issue_title="Test" \
  -f branch_name=test-branch-name \
  -f pr_number=PR_NUMBER \
  -f base_branch=master
```

## Understanding `--ref`

The `--ref` flag is critical for testing workflow changes:

- **What it does**: Runs the workflow YAML file from the specified branch
- **Not just inputs**: Changes to the workflow file itself (steps, jobs, scripts) only take effect when using `--ref your-branch`
- **Separate from `branch_name`**: The `branch_name` input is where the implementation happens; `--ref` is which workflow file to use

## Cleanup

After testing, clean up the test artifacts:

```bash
# Delete test branch
git push origin --delete test-workflow-{id}

# Close draft PR (via GitHub UI or gh pr close)
gh pr close PR_NUMBER

# Close test issue if created
gh issue close ISSUE_NUMBER
```
