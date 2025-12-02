---
completed_steps: 0
steps:
- completed: false
  text: 1. Initialize an exit code accumulator
- completed: false
  text: 2. Run each phase, OR-ing failures into the accumulator
- completed: false
  text: 3. Print a summary of which phases passed/failed
- completed: false
  text: 4. Return non-zero if any phase failed
- completed: false
  text: '1. **Exit code tracking**: `exit_code=0` starts clean, `|| exit_code=1` captures
    failures'
- completed: false
  text: '2. **Phase headers**: Echo statements before each phase for clear output'
- completed: false
  text: '3. **Inline commands**: Expand the Make target dependencies into explicit
    commands'
- completed: false
  text: '4. **Subshell for cd**: Use `(cd ... && ...)` to avoid working directory
    issues'
- completed: false
  text: '5. **Final exit**: `exit $$exit_code` returns failure if any phase failed'
- completed: false
  text: 1. Intentionally breaking one phase (e.g., add a lint error)
- completed: false
  text: 2. Run `make fast-ci`
- completed: false
  text: 3. Confirm all phases run and final exit code is non-zero
total_steps: 12
---

# Progress Tracking

- [ ] 1. Initialize an exit code accumulator
- [ ] 2. Run each phase, OR-ing failures into the accumulator
- [ ] 3. Print a summary of which phases passed/failed
- [ ] 4. Return non-zero if any phase failed
- [ ] 1. **Exit code tracking**: `exit_code=0` starts clean, `|| exit_code=1` captures failures
- [ ] 2. **Phase headers**: Echo statements before each phase for clear output
- [ ] 3. **Inline commands**: Expand the Make target dependencies into explicit commands
- [ ] 4. **Subshell for cd**: Use `(cd ... && ...)` to avoid working directory issues
- [ ] 5. **Final exit**: `exit $$exit_code` returns failure if any phase failed
- [ ] 1. Intentionally breaking one phase (e.g., add a lint error)
- [ ] 2. Run `make fast-ci`
- [ ] 3. Confirm all phases run and final exit code is non-zero