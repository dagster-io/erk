---
enriched_by_create_enhanced_plan: true
session_id: c94a2518-0d8c-4b86-ac46-874c4ad4a0e1
generated_at: 2025-11-21T10:00:00Z
---

# CI Workflow: Skip Checks During AI Implementation

## Executive Summary

Prevent CI jobs from running on incomplete code during AI implementation workflow by detecting `.submission/` folder existence and skipping CI jobs when present. This ensures clean CI history without failed checks on intermediate states. The solution uses job-level conditionals with a reusable composite action for maintainability.

## Critical Context

### GitHub Actions workflow_dispatch Affiliation

**Discovery**: Workflows triggered via `workflow_dispatch` with `--ref "$BRANCH"` are affiliated with PRs:
- Workflows run against the specified branch's HEAD commit
- Results associate with commit SHA
- If branch has PR, checks appear on PR page
- Slight delay compared to push-triggered workflows

**Why this matters**: The `implement-plan.yml` workflow triggers CI via `gh workflow run test.yml --ref "$BRANCH"`, ensuring proper PR affiliation even with manual triggering.

### GITHUB_TOKEN Limitation

**Critical constraint**: When GitHub Actions uses `GITHUB_TOKEN` to push commits, GitHub intentionally doesn't trigger CI workflows to prevent infinite loops.

**Impact on erk workflow**:
- Bot commits via `implement-plan.yml` don't auto-trigger CI
- Solution: Manual workflow triggering via `workflow_dispatch` after bot commits
- This is WHY we need `workflow_dispatch` triggers on all CI workflows

### .submission/ Folder Semantics

**Purpose**: Signals remote AI implementation request
- Created locally in `.plan/`, then copied to `.submission/`
- Git-tracked (NOT in .gitignore) as signal to GitHub Actions
- Ephemeral - deleted after successful implementation
- Acts as trigger for `implement-plan.yml` workflow

**Problem without skip logic**: Regular CI workflows (test, lint, pyright, prettier, check-sync, md-check) trigger on push when `.submission/` is present, running on incomplete code and failing.

### Job-Level Conditional Pattern

**Architecture**: Use separate check job with outputs and job dependencies
```yaml
jobs:
  check-submission:
    outputs:
      skip: ${{ steps.check.outputs.skip }}
    steps:
      - uses: ./.github/actions/check-submission

  test:
    needs: check-submission
    if: needs.check-submission.outputs.skip == 'false'
```

**Why this is superior**:
- GitHub Actions allows job-to-job data passing via outputs
- Job-level `if` prevents entire job from running (not just individual steps)
- Main job logic remains clean with zero conditionals
- Skipped jobs shown as "Skipped" in UI (not "Failed")

## Implementation Plan

### Phase 1: Create Reusable Composite Action

**File**: `.github/actions/check-submission/action.yml`

**Purpose**: Encapsulate `.submission` folder detection logic
- Check if `.submission/` directory exists
- Output `skip: true` if exists, `skip: false` otherwise
- Print skip message for visibility

**Benefits**:
- Single source of truth for detection logic
- Reusable across all CI workflows
- Easy to modify detection logic in one place

### Phase 2: Refactor CI Workflows

**Target workflows**:
1. `.github/workflows/test.yml`
2. `.github/workflows/lint.yml`
3. `.github/workflows/pyright.yml`
4. `.github/workflows/prettier.yml`
5. `.github/workflows/check-sync.yml`
6. `.github/workflows/md-check.yml`

**Pattern for each workflow**:
1. Add `check-submission` job that runs composite action
2. Configure job outputs to expose `skip` flag
3. Add `needs: check-submission` dependency to main job
4. Add `if: needs.check-submission.outputs.skip == 'false'` to main job
5. Remove any step-level conditionals (main job logic stays clean)

**Example structure**:
```yaml
jobs:
  check-submission:
    runs-on: ubuntu-latest
    outputs:
      skip: ${{ steps.check.outputs.skip }}
    steps:
      - uses: actions/checkout@v4
      - name: Check for submission folder
        id: check
        uses: ./.github/actions/check-submission

  test:  # or lint, pyright, prettier, check-sync, md-check
    needs: check-submission
    if: needs.check-submission.outputs.skip == 'false'
    runs-on: ubuntu-latest
    steps:
      # Original workflow steps (no conditionals needed)
```

### Phase 3: Testing and Validation

**Validation approach**:
1. Run `make fast-ci` to ensure no breakage
2. Test with actual `.submission/` folder:
   - Create `.submission/` directory
   - Push to branch
   - Verify CI jobs are skipped (not failed)
3. Test without `.submission/` folder:
   - Remove `.submission/` directory
   - Push to branch
   - Verify CI jobs run normally

## Session Discoveries

### Discovery Journey: From Problem to Solution

**Initial question**: "Can workflow_dispatch workflows still affiliate with PRs?"
- Examined recent commits, specifically `ceb25dc4`
- Found that workflows use `--ref "$BRANCH"` for branch-based affiliation
- Answer: Yes, they're affiliated through branch association

**Follow-up question**: "Do CI jobs handle .submission/ folder properly?"
- Examined test.yml, lint.yml, pyright.yml
- Discovered: **NO special handling exists**
- Problem identified: CI runs twice (once fails, once passes)

**User requirement**: "I want clean CI history"
- This drove the solution: skip CI entirely when `.submission/` exists
- Eliminates noisy failed checks from intermediate states

### Solution Evolution

**Iteration 1: Step-level conditionals**
- Added check step to detect `.submission/` folder
- Added `if` conditionals to every step (5-6 per workflow)
- Issues: Too much duplication, maintenance burden

**Iteration 2: Composite action + step conditionals**
- Created `.github/actions/check-submission/action.yml`
- Reused action across workflows
- Still required conditionals on every step
- User feedback: "Is there a way to make this more composable?"

**Iteration 3: Job-level conditionals (final)**
- Separate `check-submission` job with outputs
- Main job depends on check job via `needs`
- Single job-level `if` condition
- Result: Clean main job logic, minimal duplication

### Failed Attempts and Lessons

**Step-level conditional approach failed because**:
- Required `if: steps.check_submission.outputs.skip == 'false'` on every step
- 6 workflows × 4-6 steps each = 24-36 conditional checks
- High maintenance burden if detection logic changes
- Verbose and repetitive

**What was learned**:
- GitHub Actions supports job-to-job outputs
- Job-level conditionals are more powerful than step-level
- Composite actions best used for logic encapsulation, not just for step reuse

**Why job-level pattern is superior**:
- Entire job skips (not individual steps)
- Main job stays clean (zero conditionals in main logic)
- Only 2 lines per workflow: `needs` and `if`
- Detection logic centralized in composite action

### API/Tool Quirks

**GitHub Actions outputs between jobs**:
- Outputs must be declared in job's `outputs` section
- Format: `outputs: { skip: ${{ steps.check.outputs.skip }} }`
- Downstream jobs access via `needs.<job-name>.outputs.<output-name>`
- Values are strings, use `== 'false'` not `== false`

**Composite action outputs**:
- Declared in action.yml: `outputs: { skip: { value: ${{ steps.check.outputs.skip }} } }`
- Step within composite action must have matching `id`
- Uses `shell: bash` for bash commands in composite actions

**workflow_dispatch triggering**:
- Can pass `--ref` flag to specify branch
- Branch name must exist at trigger time
- Triggered workflows don't automatically appear in PR check suite initially
- May have slight delay before showing up on PR page

### Performance Considerations

**Two CI runs problem** (before solution):
- Push with `.submission/` → CI triggers immediately → runs on incomplete code → fails
- `implement-plan.yml` completes → triggers CI manually → runs on complete code → passes
- Result: Noisy CI history with failed checks

**With skip logic** (after solution):
- Push with `.submission/` → CI jobs skip entirely (shown as "Skipped")
- `implement-plan.yml` completes → triggers CI manually → runs on complete code → passes
- Result: Clean CI history with only passing checks

**Extra job overhead**:
- Each workflow now runs `check-submission` job first (~5-10 seconds)
- Minimal cost for clean CI history
- Job runs on every push, but very lightweight (just directory check)

### Technical Implementation Details

**Composite action structure**:
```yaml
name: Check for Submission Folder
description: Checks if .submission folder exists and sets skip output

outputs:
  skip:
    description: Whether to skip CI (true if .submission exists)
    value: ${{ steps.check.outputs.skip }}

runs:
  using: composite
  steps:
    - name: Check for submission folder
      id: check
      shell: bash
      run: |
        if [ -d ".submission" ]; then
          echo "skip=true" >> $GITHUB_OUTPUT
          echo "⏭️  Skipping CI - .submission folder detected"
        else
          echo "skip=false" >> $GITHUB_OUTPUT
        fi
```

**Job dependency syntax**:
- `needs: check-submission` - Creates dependency
- `if: needs.check-submission.outputs.skip == 'false'` - Conditional execution
- Jobs with unmet conditions show as "Skipped" in GitHub UI

**Local action reference**:
- `uses: ./.github/actions/check-submission` - Relative to repo root
- Requires checkout step before use
- Action files must exist at workflow runtime (committed to repo)

## Files Modified

1. `.github/actions/check-submission/action.yml` - NEW: Composite action for detection logic
2. `.github/workflows/test.yml` - MODIFIED: Add job-level conditional
3. `.github/workflows/lint.yml` - MODIFIED: Add job-level conditional
4. `.github/workflows/pyright.yml` - MODIFIED: Add job-level conditional
5. `.github/workflows/prettier.yml` - MODIFIED: Add job-level conditional
6. `.github/workflows/check-sync.yml` - MODIFIED: Add job-level conditional
7. `.github/workflows/md-check.yml` - MODIFIED: Add job-level conditional

## Success Criteria

✅ All CI workflows detect `.submission/` folder existence
✅ CI jobs skip entirely when `.submission/` present
✅ CI jobs run normally when `.submission/` absent
✅ Skipped jobs appear as "Skipped" in GitHub UI (not "Failed")
✅ `make fast-ci` passes with all checks
✅ Clean, composable implementation with minimal duplication
✅ Single source of truth for detection logic (composite action)

## Critical Notes

- **DO NOT** add `.submission/` to `.gitignore` - it must be tracked for GitHub Actions trigger
- **Skipped jobs != Failed jobs** - GitHub shows them differently in UI
- **Job-level conditionals are more powerful** than step-level for this use case
- **Composite action must be committed** before workflows can use it
- **String comparison required**: Use `== 'false'` not `== false` for outputs
