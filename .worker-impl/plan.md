# Plan: Restructure Learn to Create Plan Issues Instead of Writing Docs

## Goal

Change the learn workflow so it creates a plan issue for human review instead of writing documentation directly. This:
1. Unifies all implementation through `erk-impl` workflow
2. Gives humans control over documentation quality
3. Eliminates ugly branch names and generic commit messages
4. Removes the separate `learn-async.yml` workflow

## Current Flow
```
erk-impl → trigger-async-learn → learn-async.yml → /erk:learn writes docs → separate PR
```

## New Flow
```
erk-impl → /erk:learn (inline) → creates plan issue → human review → erk plan submit → erk-impl implements docs
```

## Changes

### 1. Modify `/erk:learn` skill (`.claude/commands/erk/learn.md`)

**Remove** the "Write Documentation" section (lines 587-632) that tells the agent to:
- Create new documents in `docs/learned/`
- Update existing documents
- Run `erk docs sync` for tripwires

**Keep** the existing "Validate and Save Learn Plan to GitHub Issue" section (lines 634-666) which already:
- Calls `erk exec plan-save-to-issue --plan-type learn`
- Links to parent via `--learned-from-issue`
- Creates plan issue with `erk-learn` label

**Result**: Learn skill analyzes sessions and creates a plan issue, but doesn't write any docs.

### 2. Modify `erk-impl.yml` workflow (`.github/workflows/erk-impl.yml`)

**Replace** "Trigger async learning" step (lines 385-393):
```yaml
- name: Trigger async learning
  run: |
    erk exec trigger-async-learn "$ISSUE_NUMBER" || echo "..."
```

**With** inline learn execution:
```yaml
- name: Create learn plan
  if: steps.implement.outputs.implementation_success == 'true' && steps.handle_outcome.outputs.has_changes == 'true'
  continue-on-error: true
  env:
    CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }}
    ISSUE_NUMBER: ${{ inputs.issue_number }}
  run: |
    echo "Creating learn plan for #$ISSUE_NUMBER..."
    claude --print \
      --model claude-haiku-4-5 \
      --output-format stream-json \
      --dangerously-skip-permissions \
      "/erk:learn $ISSUE_NUMBER"
```

### 3. Delete async learn infrastructure

**Delete files:**
- `.github/workflows/learn-async.yml` - No longer needed
- `src/erk/cli/commands/exec/scripts/trigger_async_learn.py` - No longer needed
- `packages/erk-shared/src/erk_shared/learn/trigger_async.py` - No longer needed

**Update `src/erk/cli/commands/learn/learn_cmd.py`:**
- Remove `--async` flag and `_handle_async_mode()` function
- The command becomes synchronous-only (creates plan issue directly)

### 4. Update documentation

**Update** `docs/learned/planning/learn-workflow.md`:
- Document new flow: learn creates plan issue, human reviews, submits via normal flow
- Remove references to learn-async workflow
- Add note that learn plans are queued for human review

## Files Modified

| File | Change |
|------|--------|
| `.claude/commands/erk/learn.md` | Remove doc writing, keep plan-saving |
| `.github/workflows/erk-impl.yml` | Replace trigger-async with inline learn |
| `.github/workflows/learn-async.yml` | DELETE |
| `src/erk/cli/commands/exec/scripts/trigger_async_learn.py` | DELETE |
| `packages/erk-shared/src/erk_shared/learn/trigger_async.py` | DELETE |
| `src/erk/cli/commands/learn/learn_cmd.py` | Remove --async flag |
| `docs/learned/planning/learn-workflow.md` | Update documentation |

## Verification

1. Run `erk learn <issue>` locally - should create a plan issue, NOT write docs
2. Submit a plan via `erk plan submit` - erk-impl should complete
3. Check that a learn plan issue was created with `erk-learn` label
4. Submit the learn plan - erk-impl should write the documentation
5. Verify branch name and commit message follow normal erk-impl patterns