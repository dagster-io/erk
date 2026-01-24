# Fix: Add --verbose to learn-dispatch workflow

## Problem

The `learn-dispatch.yml` workflow fails with:
```
Error: When using --print, --output-format=stream-json requires --verbose
```

The command is missing the required `--verbose` flag when using `--print` with `--output-format stream-json`.

## Root Cause

Claude CLI requires `--verbose` when combining `--print` and `--output-format stream-json`. The documentation already mentions this requirement, but there's no tripwire to catch it during code review.

## Changes

### 1. Fix the workflow (`.github/workflows/learn-dispatch.yml`)

Add `--verbose` flag to the claude command (line 84-88):

```yaml
run: |
  claude --print \
    --verbose \
    --model claude-haiku-4-5 \
    --output-format stream-json \
    --dangerously-skip-permissions \
    "/erk:learn $ISSUE_NUMBER"
```

### 2. Add tripwire (`docs/learned/architecture/claude-cli-integration.md`)

Add a tripwire to the frontmatter to catch this pattern in code reviews:

```yaml
tripwires:
  - action: "using `--output-format stream-json` with `--print` in Claude CLI"
    warning: "Must also include `--verbose`. Without it, the command fails with 'stream-json requires --verbose'."
```

### 3. Regenerate tripwires index

Run `erk docs sync` to regenerate `docs/learned/tripwires.md` with the new tripwire.

## Files to Modify

1. `.github/workflows/learn-dispatch.yml` - Add `--verbose` flag
2. `docs/learned/architecture/claude-cli-integration.md` - Add tripwire to frontmatter

## Verification

1. Run `erk docs sync` to regenerate tripwires
2. Push the fix and verify the workflow succeeds