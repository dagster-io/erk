---
completed_steps: 0
steps:
- completed: false
  text: 1. **Normal case:** Run a workflow where `.worker-impl/` exists - verify it
    gets cleaned up
- completed: false
  text: 2. **Missing folder case:** Manually delete `.worker-impl/` before cleanup
    step - verify workflow continues without error
- completed: false
  text: 3. **Already cleaned case:** Run cleanup twice - verify second run handles
    gracefully
total_steps: 3
---

# Progress Tracking

- [ ] 1. **Normal case:** Run a workflow where `.worker-impl/` exists - verify it gets cleaned up
- [ ] 2. **Missing folder case:** Manually delete `.worker-impl/` before cleanup step - verify workflow continues without error
- [ ] 3. **Already cleaned case:** Run cleanup twice - verify second run handles gracefully