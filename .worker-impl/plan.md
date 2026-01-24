# Consolidated Plan: erk-learn Documentation Plans

> **Consolidates:** #5859, #5858, #5855, #5849, #5848

## Source Plans

| Issue | Title | Items |
|-------|-------|-------|
| #5859 | TUI Command Palette for Remote PR Addressing | 12 doc items |
| #5858 | Consolidate erk-learn docs from 10 source plans | Meta-plan (COMPLETE) |
| #5855 | Add pr-address-remote command | 5 doc items |
| #5849 | Improve Claude CLI Error Reporting | 9 doc items |
| #5848 | Improve Claude CLI Error Reporting | DUPLICATE of #5849 |

## Investigation Findings

### Key Discovery: Significant Overlap and Completion

1. **#5858 reports consolidation is COMPLETE** - The meta-plan explicitly states "Zero documentation gaps remaining" for the 10 source plans it consolidated. This plan should be closed as completed.

2. **#5848 and #5849 are EXACT DUPLICATES** - Same title, same content, same learned_from_issue (#5844), same session ID. Close #5848 as duplicate.

3. **Existing Documentation is Comprehensive** - Investigation reveals extensive docs already exist:
   - TUI: `adding-commands.md`, `command-palette.md`, `command-execution.md`, `streaming-output.md`
   - Architecture: `claude-cli-integration.md`, `claude-executor-patterns.md`, `not-found-sentinel.md`
   - Commands: `optimization-patterns.md`, tripwires system

### Corrections to Original Plans

**#5859 (TUI Remote Workflow):**
- Claims "Remote Workflow Command Pattern Template" is missing, but `docs/learned/tui/adding-commands.md` already documents the dual-handler pattern thoroughly
- Claims "Execution Model Decision Matrix" is partially documented - `command-execution.md` has comprehensive coverage
- The 95% code similarity between `address_remote` and `fix_conflicts_remote` is already reflected in the documented patterns

**#5855 (Conversation-Context Extraction):**
- The "conversation-context extraction pattern" described is already implemented in multiple commands (`plan-submit.md`, `pr-address-remote.md`, `prepare.md`)
- No centralized documentation exists for this cross-cutting pattern - this is a genuine gap

**#5849 (Claude CLI Error Reporting):**
- Error event types ARE documented in `glossary.md` (ErrorEvent, NoOutputEvent, NoTurnsEvent, ProcessErrorEvent)
- `claude-cli-integration.md` and `claude-executor-patterns.md` exist but don't cover error handling strategies
- The actual error construction pattern is well-implemented but not documented

## Remaining Gaps (After Deduplication)

After removing duplicates and already-documented items, these gaps remain:

### HIGH Priority

1. **Conversation-Context Extraction Pattern** (from #5855)
   - Location: `docs/learned/claude-code/agent-commands.md` (NEW)
   - Documents pattern used by `/erk:plan-submit`, `/erk:pr-submit`, `/erk:pr-address-remote`, `/erk:prepare`
   - Covers: bottom-to-top search, priority-based pattern matching, multi-format reference extraction

2. **Claude CLI Error Reporting Format** (from #5849)
   - Location: `docs/learned/architecture/claude-cli-error-reporting.md` (NEW)
   - Documents: `Exit code N | stderr: ... | stdout: ...` format
   - Covers: Why stdout inclusion matters, 500-char truncation rationale, implementation locations

3. **Plan Metadata Dispatch Helpers** (from #5859)
   - The `_maybe_update_plan_dispatch_metadata()` function is duplicated in two files
   - Either extract to shared module OR document the pattern for consistency

### MEDIUM Priority

4. **Remote Workflow Command Pattern** (from #5859)
   - UPDATE `docs/learned/tui/adding-commands.md` with remote workflow specifics
   - Add section on workflow dispatch commands vs local streaming commands
   - Document `--model` parameter passing pattern

5. **Hybrid Agent-CLI Pattern** (from #5855)
   - UPDATE `docs/learned/architecture/command-boundaries.md` with "Agent Delegating to CLI" pattern
   - Inverse of existing "CLI Spawning Agent" section

### LOW Priority (Already Well-Documented)

6. **Dual Handler Pattern** - Already in `adding-commands.md`
7. **Streaming Output** - Already in `streaming-output.md`
8. **Sentinel Type Narrowing** - Already in `not-found-sentinel.md`
9. **Command Palette Availability** - Already in `command-palette.md`

## Implementation Steps

### Step 1: Close Duplicates and Completed Plans

Close these issues with appropriate comments:
- **#5848**: Close as duplicate of #5849
- **#5858**: Close as complete (its consolidation work is done)

### Step 2: Create New Documentation Files

1. Create `docs/learned/claude-code/agent-commands.md`:
   ```markdown
   ---
   title: Claude Code Agent Command Patterns
   read_when:
     - "creating Claude Code agent commands"
     - "implementing conversation-context extraction"
     - "building commands that search conversation history"
   tripwires:
     - action: "implementing conversation-context extraction commands"
       warning: "Reference the Conversation-Context Extraction Pattern. Search bottom-to-top with priority-ordered pattern matching."
   ---

   # Conversation-Context Extraction Pattern

   [Document the pattern from /erk:plan-submit, /erk:pr-submit, /erk:pr-address-remote, /erk:prepare]
   - Search conversation from bottom to top (recency bias)
   - Priority-ordered pattern matching
   - Multi-format reference extraction
   - Error handling for "not found"
   ```

2. Create `docs/learned/architecture/claude-cli-error-reporting.md`:
   ```markdown
   ---
   title: Claude CLI Error Reporting
   read_when:
     - "handling Claude CLI errors"
     - "interpreting PromptResult.error"
     - "working with ErrorEvent, NoOutputEvent, NoTurnsEvent, ProcessErrorEvent"
   tripwires:
     - action: "modifying Claude CLI error reporting or PromptResult.error format"
       warning: "Error messages must maintain 'Exit code N | stderr: ... | stdout: ...' format. Stdout truncated to 500 chars. Changes affect all 6 callers of execute_prompt()."
   ---

   # Claude CLI Error Reporting

   [Document the structured error format and rationale]
   ```

### Step 3: Update Existing Documentation

1. Add remote workflow section to `docs/learned/tui/adding-commands.md`
2. Add "Agent Delegating to CLI" section to `docs/learned/architecture/command-boundaries.md`

### Step 4: Add Tripwires

Add to `docs/learned/tripwires.md`:
```
**CRITICAL: Before creating Claude Code agent commands in .claude/commands/** → Read [Agent Command Patterns](claude-code/agent-commands.md) first. Filenames MUST match the command name for discoverability.

**CRITICAL: Before modifying Claude CLI error reporting or PromptResult.error format** → Read [Claude CLI Error Reporting](architecture/claude-cli-error-reporting.md) first.
```

### Step 5: Run Documentation Sync

```bash
erk docs sync
```

## Verification

1. Run `erk docs sync` to regenerate tripwires
2. Verify new docs appear in `docs/learned/index.md`
3. Search for patterns in commands to verify documentation is comprehensive
4. Run `make format` and `ty` to verify no issues

## Files to Modify/Create

**Create:**
- `docs/learned/claude-code/agent-commands.md`
- `docs/learned/architecture/claude-cli-error-reporting.md`

**Update:**
- `docs/learned/tui/adding-commands.md` (add remote workflow section)
- `docs/learned/architecture/command-boundaries.md` (add agent-to-CLI pattern)
- `docs/learned/tripwires.md` (add 2 new tripwires)

## Related Documentation

- `docs/learned/tui/adding-commands.md` - Dual handler pattern
- `docs/learned/architecture/command-boundaries.md` - CLI vs agent decisions
- `docs/learned/architecture/claude-executor-patterns.md` - ClaudeExecutor usage
- `docs/learned/glossary.md` - Error event type definitions