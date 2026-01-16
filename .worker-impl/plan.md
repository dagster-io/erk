# Plan: Add ty Error Fixing to CI Autofix Agent

## Summary

Enable the CI autofix agent to attempt fixing `ty` (type checker) errors automatically, in addition to the existing format, lint, prettier, and docs-sync fixes.

## Changes Required

### 1. Update CI Workflow (`.github/workflows/ci.yml`)

**a) Add ty failure to autofix trigger condition (lines 134-137)**

Current:
```yaml
(needs.format.result == 'failure' ||
 needs.lint.result == 'failure' ||
 needs.prettier.result == 'failure' ||
 needs.docs-check.result == 'failure')
```

Change to:
```yaml
(needs.format.result == 'failure' ||
 needs.lint.result == 'failure' ||
 needs.prettier.result == 'failure' ||
 needs.docs-check.result == 'failure' ||
 needs.ty.result == 'failure')
```

**b) Add ty error collection (after line 290)**

Add a new block to collect ty errors:
```bash
if [ "${{ needs.ty.result }}" = "failure" ]; then
  errors+="=== TY TYPE ERRORS ===\n"
  errors+="$(uv run ty check 2>&1 || true)\n\n"
fi
```

**c) Add ty to allowed tools (line 332)**

Current:
```
'Read(*),Bash(uv run ruff:*),Bash(prettier:*),Bash(make docs-sync:*),Bash(git:*)'
```

Change to:
```
'Read(*),Edit(*),Bash(uv run ruff:*),Bash(uv run ty:*),Bash(prettier:*),Bash(make docs-sync:*),Bash(git:*)'
```

Note: Adding `Edit(*)` is required because ty errors require file edits (unlike ruff/prettier which have `--fix`/`--write` flags).

### 2. Update Autofix Prompt (`.github/prompts/ci-autofix.md`)

**a) Change ty from "(NOT auto-fixable)" to regular status (line 11)**

Current:
```
- ty: {{ ty }} (NOT auto-fixable)
```

Change to:
```
- ty: {{ ty }}
```

**b) Add ty fixing rules (after line 24)**

Add:
```
- For ty type errors: read the files with errors, understand the type issue, and edit the files to fix the types. Run `uv run ty check` after fixing to verify.
```

**c) Remove prohibition on ty fixes (line 25)**

Current:
```
- DO NOT attempt to fix ty or test failures - those require human intervention
```

Change to:
```
- DO NOT attempt to fix test failures - those require human intervention
```

## Verification

After implementation:
1. Create a branch with an intentional type error
2. Push and observe CI failure on `ty` job
3. Verify autofix job triggers and attempts to fix the type error
4. Verify the fix is committed and pushed
5. Verify the subsequent CI verification passes

## Files Modified

- `.github/workflows/ci.yml` - 3 changes
- `.github/prompts/ci-autofix.md` - 3 changes