# Fix: Remove Non-Existent `check` Target from fast-ci.md

## Problem

The `/local:fast-ci` skill references a `make check` target that doesn't exist in the Makefile:

1. **Line 24**: Lists `8. **check** - Artifact synchronization validation`
2. **Line 41**: Instructs running `make format-check prettier-check md-check docs-validate test check`

But the Makefile has no `check` target. The actual `fast-ci` target (Makefile:90-102) runs:
- Lint, Format Check, Prettier Check, Markdown Check, **Exec Reference Check**, ty, Unit Tests

## Root Cause

The skill documentation is out of sync with the actual Makefile. The `check` target was likely renamed or removed, and `exec-reference-check` was added.

## Fix

**File**: `.claude/commands/local/fast-ci.md`

### Change 1: Update the CI Pipeline list (line 24)

Replace:
```
8. **check** - Artifact synchronization validation
```

With:
```
8. **exec-reference-check** - Exec subcommand reference documentation validation
```

### Change 2: Update the Phase 2 command (line 41)

Replace:
```
make format-check prettier-check md-check docs-validate test check
```

With:
```
make format-check prettier-check md-check docs-validate exec-reference-check test
```

Or better yet, simplify Phase 2 to just run `make fast-ci` which handles everything after Phase 1 passes.

## Implementation Steps

1. Edit `.claude/commands/local/fast-ci.md` to fix the two references to the non-existent `check` target

## Verification

Run `/local:fast-ci` - the devrun agent should no longer error on `make check`.