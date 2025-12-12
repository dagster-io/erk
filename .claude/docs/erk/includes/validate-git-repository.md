# Git Repository Validation

Execute: `git rev-parse --show-toplevel`

This confirms we're in a git repository and returns the repository root path.

**If the command fails:**

```
❌ Error: Could not detect repository root

Details: Not in a git repository or git command failed

Suggested action:
  1. Ensure you are in a valid git repository
  2. Run: git status (to verify git is working)
  3. Check if .git directory exists
```
