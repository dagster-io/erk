---
title: Graphite Stack Troubleshooting
read_when:
  - "PR submission fails with 'no changes' error"
  - "Graphite stack has empty branches"
  - "debugging gt upstack onto failures"
tripwires:
  - action: "Before submitting PRs in Graphite stacks"
    warning: "Validate all ancestor branches have commits. Empty branches block entire stack. Use `gt info` to diagnose, `gt upstack onto` to fix."
---

# Graphite Stack Troubleshooting

## Empty Branch Blocking Submission

**Problem**: PR submission fails with "no changes" or similar error, even though your working branch has changes.

**Root cause**: An ancestor branch in the Graphite stack has no commits (empty branch). This commonly happens when a worktree creation fails partway through, leaving a branch that was created but never received commits.

## Diagnostic Workflow

**Step 1: Check parent branch status**

See `gt info --branch <parent>` in Graphite CLI documentation for checking branch metadata including commit status.

**Step 2: List stack structure**

Use `gt ls` to visualize the entire stack and identify which branches exist.

**Step 3: Identify empty branches**

For each ancestor, check if commits exist with `git log <parent>..HEAD`. If empty, that branch is blocking.

## Resolution: Skip Empty Branch

When an empty ancestor branch is identified, use `gt upstack onto` to re-parent your branch to a valid ancestor:

See `gt upstack onto <valid-ancestor>` in Graphite CLI documentation for re-parenting branches.

This removes the empty branch from your stack lineage, allowing submission to proceed.

## Prevention

Before running PR submission workflows, validate that the current branch and all ancestors have commits. A tripwire in planning/tripwires.md covers this check.

## Related

- [PR Submit Pipeline Architecture](../cli/pr-submit-pipeline.md)
- [Planning Tripwires](../planning/tripwires.md)
