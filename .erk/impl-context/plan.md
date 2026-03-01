# Plan: Enrich remote CONFLICT_RESOLUTION_PROMPT to match local slash command

## Context

The local `/erk:rebase` slash command has rich, detailed conflict resolution guidance (auto-generated file detection, intent understanding, intelligent merging strategies, `erk docs sync` regeneration). The remote CI script's `CONFLICT_RESOLUTION_PROMPT` was never updated to match — it's been the same basic 4-line string since the script was first created in Jan 2026. The rename from "fix-conflicts" to "rebase" was purely mechanical and didn't port any prompt improvements.

This gap means remote/CI rebases get worse conflict resolution than local interactive ones. The fix: replace the basic prompt with richer guidance adapted for headless execution (no user to ask).

## Change

**File:** `src/erk/cli/commands/exec/scripts/rebase_with_conflict_resolution.py`

Replace `CONFLICT_RESOLUTION_PROMPT` (lines 150-155) with an expanded version that mirrors the slash command's steps, adapted for headless use:

```python
CONFLICT_RESOLUTION_PROMPT = """\
Fix all merge conflicts in this repository and continue the rebase.

Steps:

1. Run `git status` to identify all conflicted files.

2. For each conflicted file, check for the `<!-- AUTO-GENERATED FILE -->` header comment:
   - Auto-generated files (e.g., tripwires.md, index.md with the auto-generated header): \
Accept either side with `git checkout --theirs <file>`, stage with `git add`. \
After the rebase completes, regenerate them (e.g., `erk docs sync` for tripwires/index files).
   - Real content files: proceed to step 3.

3. For each real content file:
   a. Read the file and understand both sides of the conflict:
      - `<<<<<<< HEAD` = local changes
      - `=======` separates local from incoming
      - `>>>>>>> <commit>` = incoming changes
   b. Determine what each side was trying to accomplish.
   c. Resolve intelligently:
      - If changes are complementary → merge both
      - If changes conflict semantically → prefer the more recent/complete version
      - If genuinely unclear → prefer the incoming (upstream) version
   d. Remove all conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`).
   e. Stage the resolution: `git add <file>`

4. After resolving all conflicts:
   - Stage all resolved files with `git add`
   - Continue the rebase: `git rebase --continue`

5. If more conflicts appear, repeat from step 1.

6. After rebase completes, regenerate any auto-generated files that were resolved in step 2 \
(e.g., `erk docs sync`).
"""
```

Key adaptation from local → remote: "if unclear → ask the user" becomes "prefer the incoming (upstream) version" since this runs headlessly.

## Verification

1. Inspect the diff: the constant should expand from 4 lines to the structured multi-step prompt.
2. Run unit tests: `make fast-ci` (or `pytest tests/unit/cli/commands/exec/scripts/test_rebase_with_conflict_resolution.py`)
3. The constant is only used in `_invoke_claude_for_conflicts()` — no other callers to update.
4. No signature or interface changes; this is purely a string constant update.
