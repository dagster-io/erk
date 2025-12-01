# Switch Remote Implementation Workflow to Sonnet 4.5

## Problem

The `dispatch-erk-queue-git.yml` workflow currently uses `claude-opus-4-5-20251101` for remote plan implementation. We want to switch to `claude-sonnet-4-5-20250929` instead.

## Solution

Replace all occurrences of `claude-opus-4-5-20251101` with `claude-sonnet-4-5-20250929` in the workflow file.

## Changes

### File: `.github/workflows/dispatch-erk-queue-git.yml`

Two occurrences to change:

1. **Line 248** (Run implementation step):
   ```yaml
   --model claude-sonnet-4-5-20250929 \
   ```

2. **Line 291** (Submit branch step):
   ```yaml
   --model claude-sonnet-4-5-20250929 \
   ```