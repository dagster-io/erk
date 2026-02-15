# Plan: Optimize Learn Pipeline Context Window Usage

## Context

In session `681a0888`, the `erk learn` pipeline blew out the 200K context window at step 5 of 11. Root cause analysis reveals that **TaskOutput calls from 10 parallel agents consumed 83K tokens (41.7% of the window)** despite agents already writing their output to files. The existing "self-write solution" (documented in `docs/learned/architecture/context-efficiency.md`) handles content routing correctly, but TaskOutput is still used for synchronization, which brings the full agent response back into the parent context. The fix: replace TaskOutput-based synchronization with file-based polling.

**Token budget before/after:**

| Component | Before | After | Savings |
|-----------|--------|-------|---------|
| System prompt | ~61,500 | ~61,500 | 0 |
| 10 parallel TaskOutput calls | ~83,400 | 0 | **~83,400** |
| 3 sequential Task returns | ~24,000 | 0 | **~24,000** |
| Polling bash calls | 0 | ~1,500 | -1,500 |
| Final plan read + orchestration | ~26,500 | ~24,000 | ~2,500 |
| **Total** | **~195,400** | **~87,000** | **~108,400 (55%)** |

## Changes

### 1. Add sentinel file pattern to all 6 agent specs

Each agent spec in `.claude/agents/learn/` needs an updated Output Routing section. After writing the primary output file, the agent writes a `.done` sentinel:

**Files to modify:**
- `.claude/agents/learn/session-analyzer.md`
- `.claude/agents/learn/code-diff-analyzer.md`
- `.claude/agents/learn/existing-docs-checker.md`
- `.claude/agents/learn/documentation-gap-identifier.md`
- `.claude/agents/learn/plan-synthesizer.md`
- `.claude/agents/learn/tripwire-extractor.md`

Add to each Output Routing section:
```
After writing the primary output file, create a sentinel:
  Write ".done" to <output_path>.done
```

Order is critical: primary file first, then sentinel. The sentinel guarantees the primary output is fully written.

### 2. Create PR comment analyzer agent spec (new file)

**Create:** `.claude/agents/learn/pr-comment-analyzer.md`

Extract the inline PR Comment Analyzer prompt from `learn.md` lines 376-421 into this new agent spec. Add sentinel file support. This reduces learn.md by ~45 lines and makes the agent consistent with the other 6.

### 3. Replace TaskOutput with file-polling in learn.md

**Modify:** `.claude/commands/erk/learn.md`

Replace the "Wait for Parallel Agents and Verify Output Files" section (lines 423-439) with a bash polling loop:

```bash
LEARN_AGENTS_DIR=".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents"
TIMEOUT=600
INTERVAL=5
ELAPSED=0

while true; do
  FOUND=$(ls "$LEARN_AGENTS_DIR"/*.done 2>/dev/null | wc -l)
  if [ "$FOUND" -ge <expected_count> ]; then break; fi
  ELAPSED=$((ELAPSED + INTERVAL))
  if [ $ELAPSED -ge $TIMEOUT ]; then
    echo "TIMEOUT: Only $FOUND of <expected_count> agents completed"
    ls -la "$LEARN_AGENTS_DIR/"
    break
  fi
  sleep $INTERVAL
done
```

Remove all `TaskOutput(task_id, block: true)` calls. The orchestrator builds the expected count dynamically based on how many agents it launched.

### 4. Run sequential agents in background with file-polling

**Modify:** `.claude/commands/erk/learn.md`

Change the 3 sequential agents (gap-identifier, plan-synthesizer, tripwire-extractor) from foreground `Task()` to `Task(run_in_background: true)` + file-polling for their sentinel.

The dependency chain becomes:
```
All parallel .done sentinels exist
  -> Launch gap-identifier (background) -> poll for gap-analysis.md.done
    -> Launch plan-synthesizer (background) -> poll for learn-plan.md.done
      -> Launch tripwire-extractor (background) -> poll for tripwire-candidates.json.done
```

Each step uses the same polling pattern from change #3, just with a single expected file.

### 5. Consolidate session parts into per-session agents

**Modify:** `.claude/agents/learn/session-analyzer.md` - Change input from `session_xml_path` (single) to `session_xml_paths` (list of paths)

**Modify:** `.claude/commands/erk/learn.md` - Update Agent 1 launch logic to group XML files by session ID before launching. Instead of 1 agent per XML part, launch 1 agent per session with all its parts listed.

Example: `planning-abc-part1.xml`, `planning-abc-part2.xml`, `planning-abc-part3.xml` -> 1 agent with 3 input paths.

Safety cap: if a session has >4 parts (>80K tokens), split into groups of 3-4 parts per agent.

### 6. Update existing documentation

**Modify:** `docs/learned/architecture/parallel-agent-pattern.md` - Add "File-Polling Synchronization" section as alternative to TaskOutput. Note when to use each: TaskOutput for small agent counts where parent needs the result, file-polling for large agent counts where outputs are file-routed.

**Modify:** `docs/learned/architecture/context-efficiency.md` - Add note that file-polling completes the self-write pattern by also removing the TaskOutput synchronization overhead.

## Files Summary

| File | Action |
|------|--------|
| `.claude/commands/erk/learn.md` | Modify (remove TaskOutput, add polling, consolidate session agents) |
| `.claude/agents/learn/session-analyzer.md` | Modify (sentinel + multi-path input) |
| `.claude/agents/learn/code-diff-analyzer.md` | Modify (add sentinel) |
| `.claude/agents/learn/existing-docs-checker.md` | Modify (add sentinel) |
| `.claude/agents/learn/documentation-gap-identifier.md` | Modify (add sentinel) |
| `.claude/agents/learn/plan-synthesizer.md` | Modify (add sentinel) |
| `.claude/agents/learn/tripwire-extractor.md` | Modify (add sentinel) |
| `.claude/agents/learn/pr-comment-analyzer.md` | **Create** (extract from learn.md) |
| `docs/learned/architecture/parallel-agent-pattern.md` | Modify (add file-polling section) |
| `docs/learned/architecture/context-efficiency.md` | Modify (add synchronization note) |

## Verification

1. Run `erk learn` on a plan with multiple session parts (like plan #6996 which had 5+2 parts) and verify context usage stays under 50% of window
2. Verify all agent output files and sentinels are written correctly
3. Verify timeout handling works when an agent fails (simulate by temporarily breaking an agent spec)
4. Verify the gist_url codepath still works (preprocessed materials)
5. Run `make fast-ci` to ensure no regressions