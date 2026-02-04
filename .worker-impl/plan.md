# Delete All Work for Objective #5942 (Beads Backend)

## Summary

Remove all code, tests, documentation, and GitHub issues related to the Beads backend objective.

## Step 1: Delete source files

Delete the entire beads gateway directory:

```
packages/erk-shared/src/erk_shared/gateway/beads/
  __init__.py
  abc.py
  types.py
  real.py
  fake.py
  dry_run.py
  printing.py
```

## Step 2: Delete test files

```
tests/shared/gateway/beads/          (entire directory)
tests/integration/test_real_beads.py
```

## Step 3: Delete documentation

- `docs/learned/architecture/beads-backend-analysis.md`

## Step 4: Clean up references in other docs

- `docs/learned/architecture/index.md` — auto-generated, will regenerate after file deletion via `erk docs sync`
- `docs/learned/architecture/gateway-abc-implementation.md` — remove the BeadsGateway example reference (lines ~667-670)
- `docs/learned/reference/gastown-analysis.md` — references "beads" as a Gastown concept (not erk's BeadsGateway), leave as-is

## Step 5: Close GitHub issues

- Close objective #5942
- Close any remaining open plan issues linked to it (none found currently open)

## Step 6: Verify

- Run `devrun` agent with `make fast-ci` to confirm nothing is broken
- Run `erk docs sync` if available, or verify the index regenerates correctly

## Notes

- No code outside the beads module imports from it, so deletion is clean
- PRs #5944 and #6018 are already merged; this work removes the merged code from master
- The gastown-analysis.md references to "beads" are about the Gastown domain concept, not erk's BeadsGateway — those stay