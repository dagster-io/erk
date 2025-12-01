---
completed_steps: 0
steps:
- completed: false
  text: 1. Adding GitHubGtKit methods to GitHub(ABC) with explicit parameters
- completed: false
  text: 2. Removing GitHubGtKit entirely
- completed: false
  text: 3. Updating all callers to use the unified interface
- completed: false
  text: '1. **Incremental approach**: Add new methods first (non-breaking), then migrate
    callers, then delete old code'
- completed: false
  text: '2. **Test coverage**: Run full test suite after each step to catch regressions'
- completed: false
  text: '3. **Return type change for merge_pr**: From `None` to `bool` - callers that
    ignore return value unaffected'
total_steps: 6
---

# Progress Tracking

- [ ] 1. Adding GitHubGtKit methods to GitHub(ABC) with explicit parameters
- [ ] 2. Removing GitHubGtKit entirely
- [ ] 3. Updating all callers to use the unified interface
- [ ] 1. **Incremental approach**: Add new methods first (non-breaking), then migrate callers, then delete old code
- [ ] 2. **Test coverage**: Run full test suite after each step to catch regressions
- [ ] 3. **Return type change for merge_pr**: From `None` to `bool` - callers that ignore return value unaffected