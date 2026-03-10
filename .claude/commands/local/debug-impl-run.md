---
description: Debug a failed plan-implement workflow run
---

# Debug Implementation Run

Fetch and analyze a failed `plan-implement` GitHub Actions workflow run. Uses the REST API to get full untruncated logs, parses the embedded Claude CLI stream-json output, and produces a structured summary.

## Usage

```bash
/debug-impl-run <run_id_or_url>
```

Argument can be:

- A numeric run ID: `22902216182`
- A full GitHub Actions URL: `https://github.com/owner/repo/actions/runs/22902216182`

## Implementation

### Step 1: Run the debug command

```bash
erk exec debug-impl-run <argument> --json
```

### Step 2: Interpret the results

Parse the JSON output and present findings clearly:

- **Session info**: session ID, model, duration, cost
- **Error analysis**: What errors occurred and why
- **Tool timeline**: What the agent did (files read, files modified, commands run)
- **Assistant messages**: Key decisions the agent made

### Step 3: Diagnose the failure

Based on the summary, identify:

1. **Where it failed** — which phase or tool action
2. **Why it failed** — the root cause from error messages
3. **What to do** — suggest a fix (rerun, replan, or manual intervention)

## Finding Run IDs

If the user doesn't provide a run ID, help them find it:

```bash
# List recent workflow runs for the current branch
gh run list --branch $(git branch --show-current) --json databaseId,name,conclusion,status --jq '.[] | "\(.databaseId) \(.name) [\(.conclusion // .status)]"' | head -10
```

## Notes

- This command fetches and analyzes logs — it does NOT fix issues
- The REST API returns full untruncated logs (unlike `gh run view --log` which truncates)
- Use `--json` flag for machine-readable output
