---
description: Save the current session's plan to GitHub as an issue
---

# /erk:save-plan

Run this command and display the output to the user:

```bash
dot-agent run erk plan-save-to-issue --format display
```

On success, display the URL to the user along with the suggested next steps from the output.

On failure, display the error message and suggest:

- Checking that a plan exists (enter Plan mode and exit it first)
- Verifying GitHub CLI authentication (`gh auth status`)
- Checking network connectivity
