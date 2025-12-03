---
completed_steps: 0
steps:
- completed: false
  text: 1. **Always include `success` field** - Boolean indicating operation result
- completed: false
  text: 2. **Error uses `error` field** - Human-readable message for LLM to report
- completed: false
  text: 3. **Exit codes** - 0 for success, 1 for errors
- completed: false
  text: 4. **Use `click.echo()`** - Not `print()`, for Click integration
- completed: false
  text: 5. **Single JSON line** - No pretty-printing for machine parsing
- completed: false
  text: 1. Read `.claude/docs/dignified-python/dignified-python-core.md`
- completed: false
  text: 2. Add B904 exception chaining section after line 114
- completed: false
  text: 3. Read `docs/agent/kits/cli-commands.md`
- completed: false
  text: 4. Add JSON output pattern section at end of file
- completed: false
  text: 5. Run `make fast-ci` to verify no formatting issues
total_steps: 10
---

# Progress Tracking

- [ ] 1. **Always include `success` field** - Boolean indicating operation result
- [ ] 2. **Error uses `error` field** - Human-readable message for LLM to report
- [ ] 3. **Exit codes** - 0 for success, 1 for errors
- [ ] 4. **Use `click.echo()`** - Not `print()`, for Click integration
- [ ] 5. **Single JSON line** - No pretty-printing for machine parsing
- [ ] 1. Read `.claude/docs/dignified-python/dignified-python-core.md`
- [ ] 2. Add B904 exception chaining section after line 114
- [ ] 3. Read `docs/agent/kits/cli-commands.md`
- [ ] 4. Add JSON output pattern section at end of file
- [ ] 5. Run `make fast-ci` to verify no formatting issues