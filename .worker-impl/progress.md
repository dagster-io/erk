---
completed_steps: 0
steps:
  - completed: false
    text: "1. **Python layer**: `pr_update.py` returns a generic error (no `error_type`)"
  - completed: false
    text:
      "2. **Agent layer**: The calling agent tries to auto-fix with `gt sync`, which
      hangs on interactive prompts"
  - completed: false
    text: '1. **Python layer** - Return structured error with `error_type: "submit_diverged"`'
  - completed: false
    text:
      2. **Agent markdown layer** - Add explicit `submit_diverged` response handling
      to signal this is a terminal error requiring user action
  - completed: false
    text: 1. **`packages/erk-shared/src/erk_shared/integrations/gt/kit_cli_commands/gt/pr_update.py`**
  - completed: false
    text: 2. **`packages/dot-agent-kit/tests/unit/kits/gt/test_pr_update.py`**
  - completed: false
    text:
      3. **`packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/agents/gt/gt-update-pr-submitter.md`**
      (canonical)
  - completed: false
    text: 4. **`.claude/agents/gt/gt-update-pr-submitter.md`** (local copy)
total_steps: 8
---

# Progress Tracking

- [ ] 1. **Python layer**: `pr_update.py` returns a generic error (no `error_type`)
- [ ] 2. **Agent layer**: The calling agent tries to auto-fix with `gt sync`, which hangs on interactive prompts
- [ ] 1. **Python layer** - Return structured error with `error_type: "submit_diverged"`
- [ ] 2. **Agent markdown layer** - Add explicit `submit_diverged` response handling to signal this is a terminal error requiring user action
- [ ] 1. **`packages/erk-shared/src/erk_shared/integrations/gt/kit_cli_commands/gt/pr_update.py`**
- [ ] 2. **`packages/dot-agent-kit/tests/unit/kits/gt/test_pr_update.py`**
- [ ] 3. **`packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/agents/gt/gt-update-pr-submitter.md`** (canonical)
- [ ] 4. **`.claude/agents/gt/gt-update-pr-submitter.md`** (local copy)
