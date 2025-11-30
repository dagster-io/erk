---
completed_steps: 0
steps:
  - completed: false
    text:
      "1. **Kit CLI command** (`fetch-run-logs`): Handles deterministic work - parsing
      run references, fetching logs via `gh`, extracting failure metadata"
  - completed: false
    text:
      "2. **Claude command** (`debug-run.md`): Invokes kit command and performs
      semantic analysis of failures"
  - completed: false
    text:
      1. **URL parsing follows `parse_issue_reference.py` pattern** - Regex for
      URL, `isdigit()` for plain numbers
  - completed: false
    text:
      2. **Use `gh run view --log` not `--log-failed`** - `--log-failed` only shows
      failed steps which loses context; full logs provide better analysis material
  - completed: false
    text:
      3. **Save logs to `.erk/scratch/`** - Full logs saved to disk for reference;
      Claude command reads the file for analysis
  - completed: false
    text:
      4. **Kit command does NO semantic analysis** - Just fetches/formats data;
      all interpretation done by Claude
  - completed: false
    text: 5. **Recommend only, no auto-apply** - Per user requirement
total_steps: 7
---

# Progress Tracking

- [ ] 1. **Kit CLI command** (`fetch-run-logs`): Handles deterministic work - parsing run references, fetching logs via `gh`, extracting failure metadata
- [ ] 2. **Claude command** (`debug-run.md`): Invokes kit command and performs semantic analysis of failures
- [ ] 1. **URL parsing follows `parse_issue_reference.py` pattern** - Regex for URL, `isdigit()` for plain numbers
- [ ] 2. **Use `gh run view --log` not `--log-failed`** - `--log-failed` only shows failed steps which loses context; full logs provide better analysis material
- [ ] 3. **Save logs to `.erk/scratch/`** - Full logs saved to disk for reference; Claude command reads the file for analysis
- [ ] 4. **Kit command does NO semantic analysis** - Just fetches/formats data; all interpretation done by Claude
- [ ] 5. **Recommend only, no auto-apply** - Per user requirement
