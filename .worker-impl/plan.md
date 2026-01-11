# Document Autolearn Feature

Add documentation for the autolearn feature introduced in PR #4684.

## Context

The autolearn feature automatically creates a learn plan issue when landing a PR via `erk land`. This captures session insights before they're lost.

**Key Files:**
- `src/erk/cli/commands/autolearn.py` - Core autolearn logic
- `src/erk/cli/commands/land_cmd.py` - Integration into land command
- `packages/erk-shared/src/erk_shared/context/types.py` - GlobalConfig with autolearn setting
- `packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py` - Config loading

**Design Pattern:**
- Follows `objective_helpers.py` fail-open pattern
- Never fails the landing operation even if autolearn errors
- Config-based enablement via `~/.erk/config.yaml`

## Raw Materials

https://gist.github.com/schrockn/0ec2635ffb0532f4c82cebfcbe535057

## Documentation Items

### 1. Update docs/learned/erk/index.md

**Location:** `docs/learned/erk/index.md`
**Action:** Update
**Source:** Implementation analysis

Add entry for autolearn to the erk features index.

### 2. Create docs/learned/erk/autolearn.md

**Location:** `docs/learned/erk/autolearn.md`
**Action:** Create
**Source:** PR #4684, plan #4681

Document the autolearn feature with:

**Content:**
- What it does: Automatically creates a learn plan issue after `erk land` merges a PR
- Configuration: `autolearn: true` in `~/.erk/config.yaml`
- CLI override: `--no-autolearn` flag on `erk land`
- Behavior: Fail-open (errors don't block landing)
- When it triggers: Only for PRs that reference an erk-plan issue
- What it creates: A learn plan issue with session IDs for later processing

### 3. Update docs/learned/planning/lifecycle.md

**Location:** `docs/learned/planning/lifecycle.md`
**Action:** Update
**Source:** New workflow integration

Add autolearn to the plan lifecycle documentation as a post-land step:
- Plan created → Plan implemented → PR landed → **Autolearn captures sessions**

### 4. Update docs/learned/cli/index.md

**Location:** `docs/learned/cli/index.md`
**Action:** Update
**Source:** New CLI option

Document the `--no-autolearn` flag on `erk land` command.