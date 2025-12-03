---
completed_steps: 0
steps:
- completed: false
  text: 1. CLI (`auto_restack_cmd.py`) delegates to Claude slash command (`/erk:auto-restack`)
- completed: false
  text: 2. Slash command runs `gt restack --no-interactive` and handles conflicts
- completed: false
  text: '3. Result: branch is restacked but may have multiple commits'
- completed: false
  text: 1. **Check if squash was disabled** - If `--no-squash` was passed, skip to
    Step 5
- completed: false
  text: '2. **Count branch commits**:'
- completed: false
  text: '3. **Squash if 2+ commits** - If count >= 2, run:'
- completed: false
  text: '4. **Handle squash conflicts** - If squash fails with conflicts:'
- completed: false
  text: 1. CLI adds `--no-squash` flag -> appends to command string
- completed: false
  text: 2. Slash command parses argument -> skips squash step if present
- completed: false
  text: '3. Default behavior: squash after restack completes'
total_steps: 10
---

# Progress Tracking

- [ ] 1. CLI (`auto_restack_cmd.py`) delegates to Claude slash command (`/erk:auto-restack`)
- [ ] 2. Slash command runs `gt restack --no-interactive` and handles conflicts
- [ ] 3. Result: branch is restacked but may have multiple commits
- [ ] 1. **Check if squash was disabled** - If `--no-squash` was passed, skip to Step 5
- [ ] 2. **Count branch commits**:
- [ ] 3. **Squash if 2+ commits** - If count >= 2, run:
- [ ] 4. **Handle squash conflicts** - If squash fails with conflicts:
- [ ] 1. CLI adds `--no-squash` flag -> appends to command string
- [ ] 2. Slash command parses argument -> skips squash step if present
- [ ] 3. Default behavior: squash after restack completes