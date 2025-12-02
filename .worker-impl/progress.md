---
completed_steps: 0
steps:
- completed: false
  text: 1. Checks for restack conflicts (abort if any - do NOT resolve)
- completed: false
  text: 2. Squashes commits
- completed: false
  text: 3. Generates AI commit message (reusing `commit-message-generator` agent)
- completed: false
  text: 4. Amends the commit with that message
- completed: false
  text: 5. **Stops there** (no push, no PR creation/update)
- completed: false
  text: 1. Clean branch → verify squash + message update works
- completed: false
  text: 2. Restack conflicts → verify abort with helpful message
- completed: false
  text: 3. Single commit → verify no squash, just message update
- completed: false
  text: 4. Verify message matches what `/gt:pr-submit` would produce
total_steps: 9
---

# Progress Tracking

- [ ] 1. Checks for restack conflicts (abort if any - do NOT resolve)
- [ ] 2. Squashes commits
- [ ] 3. Generates AI commit message (reusing `commit-message-generator` agent)
- [ ] 4. Amends the commit with that message
- [ ] 5. **Stops there** (no push, no PR creation/update)
- [ ] 1. Clean branch → verify squash + message update works
- [ ] 2. Restack conflicts → verify abort with helpful message
- [ ] 3. Single commit → verify no squash, just message update
- [ ] 4. Verify message matches what `/gt:pr-submit` would produce