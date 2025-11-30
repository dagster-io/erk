---
completed_steps: 0
steps:
  - completed: false
    text:
      "1. **Remote by default**: `erk plan` creates/reuses Codespace and auto-executes
      `/erk:craft-plan`"
  - completed: false
    text: "2. **Local option**: `erk plan --local` runs planning in current directory"
  - completed: false
    text:
      "3. **Auto-execute Claude**: SSH with command execution, not interactive SSH
      + manual invocation"
  - completed: false
    text:
      "4. **Replace `erk codespace plan`**: Move functionality to `erk plan`, remove
      from codespace group"
  - completed: false
    text:
      "5. **Keep `erk codespace init`**: Infrastructure setup remains under codespace
      group"
  - completed: false
    text: 1. `erk plan` - triggers remote planning flow
  - completed: false
    text: 2. `erk plan --local` - triggers local planning flow
  - completed: false
    text: 3. `erk plan "description"` - passes description correctly
  - completed: false
    text: 4. `erk plan list` - existing subcommand still works
  - completed: false
    text: 5. `erk plan get 42` - existing subcommand still works
  - completed: false
    text: 6. `erk plan --help` - shows correct help with options and subcommands
  - completed: false
    text: 7. `erk codespace plan` - no longer exists (or shows deprecation warning)
total_steps: 12
---

# Progress Tracking

- [ ] 1. **Remote by default**: `erk plan` creates/reuses Codespace and auto-executes `/erk:craft-plan`
- [ ] 2. **Local option**: `erk plan --local` runs planning in current directory
- [ ] 3. **Auto-execute Claude**: SSH with command execution, not interactive SSH + manual invocation
- [ ] 4. **Replace `erk codespace plan`**: Move functionality to `erk plan`, remove from codespace group
- [ ] 5. **Keep `erk codespace init`**: Infrastructure setup remains under codespace group
- [ ] 1. `erk plan` - triggers remote planning flow
- [ ] 2. `erk plan --local` - triggers local planning flow
- [ ] 3. `erk plan "description"` - passes description correctly
- [ ] 4. `erk plan list` - existing subcommand still works
- [ ] 5. `erk plan get 42` - existing subcommand still works
- [ ] 6. `erk plan --help` - shows correct help with options and subcommands
- [ ] 7. `erk codespace plan` - no longer exists (or shows deprecation warning)
