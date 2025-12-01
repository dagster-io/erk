---
completed_steps: 0
steps:
- completed: false
  text: '1. **State detection approach**: User selected "Separate command" - Create
    distinct `erk-dev publish-release` command for the publish-only step. This changes
    the implementation from adding `--skip-prepare` flag to creating a new command.'
- completed: false
  text: '2. **Validation timing**: User selected "Always validate" - Run all validation
    in prepare phase to fail early before any changes are made.'
- completed: false
  text: '3. **Missing artifacts behavior**: User selected "Error and exit" - Exit
    with clear error message directing user to run `make prepare` first rather than
    falling through to full workflow.'
- completed: false
  text: '1. **PREPARE phase** (lines 463-508 in command.py):'
- completed: false
  text: '2. **PUBLISH phase** (lines 510-516 in command.py):'
- completed: false
  text: 1. **Create `erk-dev prepare-release` command**
- completed: false
  text: 2. **Create `erk-dev publish-release` command**
- completed: false
  text: 3. **Extract shared utilities**
- completed: false
  text: 4. **Update Makefile with new targets**
- completed: false
  text: 5. **Register new commands in CLI**
- completed: false
  text: 6. **Add tests for new commands**
- completed: false
  text: 1. **`packages/erk-dev/src/erk_dev/commands/prepare_release/__init__.py`**
- completed: false
  text: 2. **`packages/erk-dev/src/erk_dev/commands/prepare_release/command.py`**
- completed: false
  text: 3. **`packages/erk-dev/src/erk_dev/commands/publish_release/__init__.py`**
- completed: false
  text: 4. **`packages/erk-dev/src/erk_dev/commands/publish_release/command.py`**
- completed: false
  text: 1. **`packages/erk-dev/src/erk_dev/commands/publish_to_pypi/command.py`**
- completed: false
  text: 2. **`packages/erk-dev/src/erk_dev/cli.py`**
- completed: false
  text: 3. **`Makefile`**
total_steps: 18
---

# Progress Tracking

- [ ] 1. **State detection approach**: User selected "Separate command" - Create distinct `erk-dev publish-release` command for the publish-only step. This changes the implementation from adding `--skip-prepare` flag to creating a new command.
- [ ] 2. **Validation timing**: User selected "Always validate" - Run all validation in prepare phase to fail early before any changes are made.
- [ ] 3. **Missing artifacts behavior**: User selected "Error and exit" - Exit with clear error message directing user to run `make prepare` first rather than falling through to full workflow.
- [ ] 1. **PREPARE phase** (lines 463-508 in command.py):
- [ ] 2. **PUBLISH phase** (lines 510-516 in command.py):
- [ ] 1. **Create `erk-dev prepare-release` command**
- [ ] 2. **Create `erk-dev publish-release` command**
- [ ] 3. **Extract shared utilities**
- [ ] 4. **Update Makefile with new targets**
- [ ] 5. **Register new commands in CLI**
- [ ] 6. **Add tests for new commands**
- [ ] 1. **`packages/erk-dev/src/erk_dev/commands/prepare_release/__init__.py`**
- [ ] 2. **`packages/erk-dev/src/erk_dev/commands/prepare_release/command.py`**
- [ ] 3. **`packages/erk-dev/src/erk_dev/commands/publish_release/__init__.py`**
- [ ] 4. **`packages/erk-dev/src/erk_dev/commands/publish_release/command.py`**
- [ ] 1. **`packages/erk-dev/src/erk_dev/commands/publish_to_pypi/command.py`**
- [ ] 2. **`packages/erk-dev/src/erk_dev/cli.py`**
- [ ] 3. **`Makefile`**