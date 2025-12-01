---
completed_steps: 0
total_steps: 14
---

# Progress Tracking

- [ ] 1. Validates issue has `erk-queue` label and is OPEN
- [ ] 2. Parses comments to find retry count
- [ ] 3. Removes and re-adds `erk-queue` label (triggers workflow via webhook)
- [ ] 4. Posts metadata comment with retry info
- [ ] 5. Shows success message with issue URL only
- [ ] 1. Adds `erk-queue` label to issue
- [ ] 2. Triggers workflow via API (`ctx.github.trigger_workflow()`)
- [ ] 3. Gets run ID back from API
- [ ] 4. Constructs workflow URL from run ID
- [ ] 5. Displays workflow URL to user
- [ ] 6. Fails fast if API trigger fails
- [ ] 1. **Dual trigger approach**: Keep label manipulation AND add API trigger
- [ ] 2. **Non-fail-fast error handling**: Show warnings but continue execution
- [ ] 3. **URL as supplementary info**: Workflow URL is "nice to have" not critical path
