---
completed_steps: 0
total_steps: 13
---

# Progress Tracking

- [ ] 1. **Input method**: User specified that optimal markdown orchestration is the priority - this confirms the combined command should eliminate the temp file entirely by reading from stdin, which is the most efficient path for markdown orchestration (no disk I/O).
- [ ] 2. **Deprecation**: User confirmed immediate removal of old commands - no deprecation period needed. This simplifies Phase 3 to just deleting the old files rather than adding deprecation warnings.
- [ ] 1. Use haiku model (simple orchestration task)
- [ ] 2. Combine two kit CLI commands into one (eliminate temp file, reduce overhead)
- [ ] 3. Simplify output instructions (reduce agent work)
- [ ] 1. Extract latest plan from ~/.claude/plans/
- [ ] 2. Create GitHub issue with plan content (schema v2 format)
- [ ] 1. Use the new `plan-save-to-issue` command (if appropriate), OR
- [ ] 2. Read directly from `~/.claude/plans/` via inline logic
- [ ] 1. Run `/erk:plan-save` - verify:
- [ ] 2. Run `/erk:plan-save-enriched` - verify it still works after include update
- [ ] 3. Run tests: `pytest packages/dot-agent-kit/tests/unit/kits/erk/test_plan_save_to_issue.py`
- [ ] 4. Verify old commands removed from `dot-agent run erk --help`
