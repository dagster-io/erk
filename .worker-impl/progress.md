---
completed_steps: 0
steps:
- completed: false
  text: '1. **Delete the command file**: `.claude/commands/erk/example-command.md`'
- completed: false
  text: '2. **Delete symlink target** (if kit command): `packages/.../commands/erk/example-command.md`'
- completed: false
  text: '3. **Search for references**:'
- completed: false
  text: '4. **Update kit.yaml**: Remove from `artifacts.command` list'
- completed: false
  text: '5. **Update dot-agent.toml**: Remove from `artifacts` array'
- completed: false
  text: '6. **Update tests**: Fix any assertions expecting the command'
- completed: false
  text: '7. **Update docs**: Remove references in workflow documentation'
- completed: false
  text: 1. **Create the artifact file** in the appropriate location
- completed: false
  text: '2. **Register in kit.yaml**:'
- completed: false
  text: '3. **Run kit sync**: `dot-agent kit sync`'
- completed: false
  text: '4. **Verify**: Symlink created in `.claude/commands/`'
- completed: false
  text: 1. **Delete artifact file** from kit source
- completed: false
  text: 2. **Delete symlink** in `.claude/` (if exists)
- completed: false
  text: '3. **Update kit.yaml**: Remove from artifacts list'
- completed: false
  text: '4. **Update dot-agent.toml**: Remove from installed artifacts'
- completed: false
  text: 5. **Delete associated tests**
- completed: false
  text: '6. **Update registry-entry.md**: Remove from artifact list'
- completed: false
  text: 1. **Delete Python file** from `kit_cli_commands/`
- completed: false
  text: 2. **Remove entry** from `kit.yaml` kit_cli_commands list
- completed: false
  text: 3. **Delete unit tests** for the command
- completed: false
  text: 1. **Enter Plan Mode** - Claude enters automatically for complex tasks, or
    manually via EnterPlanMode tool
- completed: false
  text: 2. **Create Plan** - Interactive planning with context extraction
- completed: false
  text: 3. **Exit Plan Mode** - Plan saved to `~/.claude/plans/`
- completed: false
  text: 4. **Save to GitHub** - Run `/erk:save-plan` to create GitHub issue with `erk-plan`
    label
- completed: false
  text: 5. **Implement** - Run `erk implement <issue-number>` to create worktree and
    execute plan
total_steps: 25
---

# Progress Tracking

- [ ] 1. **Delete the command file**: `.claude/commands/erk/example-command.md`
- [ ] 2. **Delete symlink target** (if kit command): `packages/.../commands/erk/example-command.md`
- [ ] 3. **Search for references**:
- [ ] 4. **Update kit.yaml**: Remove from `artifacts.command` list
- [ ] 5. **Update dot-agent.toml**: Remove from `artifacts` array
- [ ] 6. **Update tests**: Fix any assertions expecting the command
- [ ] 7. **Update docs**: Remove references in workflow documentation
- [ ] 1. **Create the artifact file** in the appropriate location
- [ ] 2. **Register in kit.yaml**:
- [ ] 3. **Run kit sync**: `dot-agent kit sync`
- [ ] 4. **Verify**: Symlink created in `.claude/commands/`
- [ ] 1. **Delete artifact file** from kit source
- [ ] 2. **Delete symlink** in `.claude/` (if exists)
- [ ] 3. **Update kit.yaml**: Remove from artifacts list
- [ ] 4. **Update dot-agent.toml**: Remove from installed artifacts
- [ ] 5. **Delete associated tests**
- [ ] 6. **Update registry-entry.md**: Remove from artifact list
- [ ] 1. **Delete Python file** from `kit_cli_commands/`
- [ ] 2. **Remove entry** from `kit.yaml` kit_cli_commands list
- [ ] 3. **Delete unit tests** for the command
- [ ] 1. **Enter Plan Mode** - Claude enters automatically for complex tasks, or manually via EnterPlanMode tool
- [ ] 2. **Create Plan** - Interactive planning with context extraction
- [ ] 3. **Exit Plan Mode** - Plan saved to `~/.claude/plans/`
- [ ] 4. **Save to GitHub** - Run `/erk:save-plan` to create GitHub issue with `erk-plan` label
- [ ] 5. **Implement** - Run `erk implement <issue-number>` to create worktree and execute plan