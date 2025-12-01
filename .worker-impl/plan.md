# Plan: Remove erk-generated commit message marker

## Summary

Delete all code related to the `<!-- erk-generated commit message -->` marker. The marker was intended as a validation gate to ensure the AI agent successfully generated a commit message, but AIs work around it, making it ineffective.

## Files to Modify

### 1. `packages/erk-shared/src/erk_shared/integrations/gt/kit_cli_commands/gt/submit_branch.py`

**Delete:**
- Line 75: `ERK_COMMIT_MESSAGE_MARKER` constant
- Lines 79-92: `_is_valid_commit_message()` function
- Lines 95-106: `_strip_commit_message_marker()` function
- Lines 854-865: Validation check in `execute_finalize()` that returns `PostAnalysisError` when marker missing
- Line 870: Call to `_strip_commit_message_marker()`

**Keep:**
- The `final_body = pr_body + metadata_section` line (just remove the subsequent strip call)

### 2. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/agents/gt/commit-message-generator.md`

**Delete:**
- Line 63: Instruction requiring marker at end of output
- Line 101 (approx): Example showing marker in output

### 3. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/commands/gt/pr-submit.md`

**Delete:**
- Lines 86-87: Documentation about checking for marker presence

### 4. `packages/dot-agent-kit/tests/unit/kits/gt/test_submit_branch.py`

**Delete:**
- `TestIsValidCommitMessage` class (lines 787-809)
- `TestStripCommitMessageMarker` class (lines 812-848)
- Update tests in `TestExecuteFinalize` that include the marker in test data - remove marker from test inputs
- Delete `test_finalize_fails_when_marker_missing()` test
- Update `test_finalize_strips_commit_message_marker()` - delete since stripping no longer happens

## Implementation Order

1. Remove marker from agent instructions (`commit-message-generator.md`)
2. Remove marker documentation (`pr-submit.md`)
3. Remove marker code from `submit_branch.py`:
   - Delete constant
   - Delete helper functions
   - Delete validation block in `execute_finalize()`
   - Delete strip call
4. Update/delete tests in `test_submit_branch.py`
5. Run tests to verify nothing breaks

## Verification

- Run `uv run pytest packages/dot-agent-kit/tests/unit/kits/gt/test_submit_branch.py -v`
- Run `uv run pyright packages/erk-shared/src/erk_shared/integrations/gt/kit_cli_commands/gt/submit_branch.py`