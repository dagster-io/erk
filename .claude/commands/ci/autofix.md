# CI Autofix

You are an implementation finalizer for CI. Your task is to run `make fast-ci` and iteratively fix any issues until all CI checks pass successfully.

## Your Mission

Run the fast CI pipeline (`make fast-ci`) and automatically fix any failures. Keep iterating until all checks pass or you get stuck on an issue that requires human intervention.

## Iteration Process

Load the `ci-iteration` skill for the iterative fix workflow.

**IMPORTANT**: In CI print mode, run Bash commands directly (not via devrun agents).

## After All Checks Pass

Commit and push the fixes:

```bash
git add -A
git commit -m "style: auto-fix CI errors"
git push
```

## Begin Now

Start by running `make fast-ci` from the repository root. Track your progress with TodoWrite and report your final status clearly.
