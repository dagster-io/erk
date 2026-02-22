## Summary

- Add `--for-plan` and `--new-slot` options to `erk br co` command, enabling plan resolution and `.impl/` setup directly from checkout
- Replace all `erk br create --for-plan` references with `erk br co --for-plan` across source, tests, docs, and agent specs
- Update `IssueNextSteps` and `DraftPRNextSteps` to emit copy-pasteable `co`-based commands instead of natural language descriptions
- Update `plan-save.md` agent spec with co-based slot options

## Test plan

- [x] All 5,585 tests pass
- [x] Lint, format, and type checks pass
- [x] New tests for `erk br co --for-plan` and `--new-slot` flags
- [x] Updated next_steps tests verify co-based commands
- [x] All stale `erk br create --for-plan` references updated across 32 files

---

To checkout this PR in a fresh worktree and environment locally, run:

```
source "$(erk pr checkout 7795 --script)" && erk pr sync --dangerous
```

🤖 Generated with [Claude Code](https://claude.com/claude-code)