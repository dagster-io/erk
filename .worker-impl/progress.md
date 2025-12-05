---
completed_steps: 0
steps:
- completed: false
  text: 1. Handler calls `pr_group` with args `["submit", "--script"]`
- completed: false
  text: 2. Click routes to `pr_submit` which doesn't have `--script` option
- completed: false
  text: '3. Click fails with "No such option: --script" but error is swallowed'
- completed: false
  text: '4. Result: exit code 1, no output to user'
- completed: false
  text: 1. For `erk pr land`, tries `"pr land"` → found → invokes `pr_land` with `--script`
- completed: false
  text: 2. For `erk pr submit`, tries `"pr submit"` → not found → tries `"pr"` → not
    found → passthrough
- completed: false
  text: 1. Verify the new section appears in shell-integration-patterns.md
- completed: false
  text: 2. Ensure it's linked from the architecture index
- completed: false
  text: 3. Verify it shows up in appropriate "read_when" conditions
total_steps: 9
---

# Progress Tracking

- [ ] 1. Handler calls `pr_group` with args `["submit", "--script"]`
- [ ] 2. Click routes to `pr_submit` which doesn't have `--script` option
- [ ] 3. Click fails with "No such option: --script" but error is swallowed
- [ ] 4. Result: exit code 1, no output to user
- [ ] 1. For `erk pr land`, tries `"pr land"` → found → invokes `pr_land` with `--script`
- [ ] 2. For `erk pr submit`, tries `"pr submit"` → not found → tries `"pr"` → not found → passthrough
- [ ] 1. Verify the new section appears in shell-integration-patterns.md
- [ ] 2. Ensure it's linked from the architecture index
- [ ] 3. Verify it shows up in appropriate "read_when" conditions