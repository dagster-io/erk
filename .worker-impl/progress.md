---
completed_steps: 0
steps:
- completed: false
  text: 1. **Global flags must be stripped before command lookup** - When the shell
    wrapper passes args like `('--debug', 'pr', 'land')`, the handler must strip `--debug`
    before matching against `SHELL_INTEGRATION_COMMANDS`
- completed: false
  text: '2. **Failure mode**: Without stripping, compound command lookup fails:'
- completed: false
  text: '3. **Known global flags to strip**: `--debug`, `--dry-run`, `--verbose`,
    `-v`'
- completed: false
  text: '1. Decide location: extend `script-mode.md` or create `shell-integration-handler.md`'
- completed: false
  text: 2. Add the global flag handling documentation
- completed: false
  text: 3. Add debugging section with examples
- completed: false
  text: 4. Update `docs/agent/index.md` with "read when" condition
total_steps: 7
---

# Progress Tracking

- [ ] 1. **Global flags must be stripped before command lookup** - When the shell wrapper passes args like `('--debug', 'pr', 'land')`, the handler must strip `--debug` before matching against `SHELL_INTEGRATION_COMMANDS`
- [ ] 2. **Failure mode**: Without stripping, compound command lookup fails:
- [ ] 3. **Known global flags to strip**: `--debug`, `--dry-run`, `--verbose`, `-v`
- [ ] 1. Decide location: extend `script-mode.md` or create `shell-integration-handler.md`
- [ ] 2. Add the global flag handling documentation
- [ ] 3. Add debugging section with examples
- [ ] 4. Update `docs/agent/index.md` with "read when" condition