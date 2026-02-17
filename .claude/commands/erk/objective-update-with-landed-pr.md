---
description: Update objective issue after landing a PR
---

# /erk:objective-update-with-landed-pr

Update an objective issue after landing a PR from a plan branch.

## Usage

Run after landing a PR:

```bash
/erk:objective-update-with-landed-pr
```

---

## Agent Instructions

### Step 0: Fetch All Context

Check `$ARGUMENTS` for optional overrides:

- `--pr <number>`: PR number that was just landed
- `--objective <number>`: Objective issue number to update
- `--branch <name>`: Original branch name
- `--auto-close`: If set and all steps are complete, close objective without asking

Run a single command to fetch and parse everything (all options are auto-discovered if omitted):

```bash
erk exec objective-fetch-context [--pr <number>] [--objective <number>] [--branch <name>]
```

This returns JSON with:

- `objective`: Issue body, title, labels, URL
- `plan`: Plan issue body and title
- `pr`: PR title, body, URL
- `roadmap.matched_steps`: Step IDs where `plan == #<plan_number>` (deterministic match)
- `roadmap.phases`: Serialized roadmap phases
- `roadmap.summary`: Step counts (done, pending, etc.)
- `roadmap.next_step`: First pending step or null
- `roadmap.all_complete`: True if every step is done or skipped

If this returns `success: false`, display the error and stop.

### Step 1: Delegate to Subagent

Use the Task tool to spawn a specialized subagent. Pass the full JSON context blob and the `--auto-close` flag if present.

**Subagent Instructions:**

You are updating objective issue #<objective-number> after landing PR #<pr-number>.

Your tasks:

1. **Read `matched_steps` from the context blob.** These are the steps this plan completed — no analysis needed. If `matched_steps` is empty, the plan may not have been linked to specific steps; fall back to comparing the plan body against the roadmap to identify which steps were completed.

2. **Update roadmap steps** using a SINGLE batched command:

**CRITICAL: Pass ALL completed steps as multiple `--step` flags in ONE command.**

```bash
erk exec update-roadmap-step <objective-number> --step <step-id-1> --step <step-id-2> ... --pr "#<pr-number>" --plan "#<plan-number>" --status done --include-body
```

Preserve the existing plan reference for each step (available in `roadmap.phases`). The `--include-body` flag returns the fully-mutated body as `updated_body` — use this for prose reconciliation (do NOT re-fetch via `gh issue view`).

3. **Perform prose reconciliation.** Compare `updated_body` against what the PR actually did:
   - Read each Design Decision. Did the PR override or refine any?
   - Read Implementation Context. Does the architecture description still match?
   - Read upcoming step descriptions. Did this PR change the landscape?
   - If nothing is stale, skip body update entirely.

| Contradiction Type          | Example                                                      | Section to Update                             |
| --------------------------- | ------------------------------------------------------------ | --------------------------------------------- |
| **Decision override**       | Objective says "Use polling", PR implemented WebSockets      | Design Decisions                              |
| **Scope change**            | Step says "Add 3 methods", PR only needed 2                  | Step description in roadmap                   |
| **Architecture drift**      | Context says "config in config.py", PR moved it to settings/ | Implementation Context                        |
| **Constraint invalidation** | Requirement listed is no longer valid                        | Implementation Context                        |
| **New discovery**           | PR revealed a caching bug affecting future steps             | Implementation Context or new Design Decision |

4. **Post the action comment** via the exec script. Provide structured JSON on stdin:

```bash
echo '{"issue_number": <N>, "date": "YYYY-MM-DD", "pr_number": <N>, "phase_step": "X.Y, X.Z", "title": "Brief title", "what_was_done": ["..."], "lessons_learned": ["..."], "roadmap_updates": ["Step X.Y: status -> done"], "body_reconciliation": [{"section": "...", "change": "..."}]}' | erk exec objective-post-action-comment
```

**Inferring content (DO NOT ask the user):**

- **What Was Done:** Infer from PR title, description, and plan body.
- **Lessons Learned:** Infer from implementation patterns. If straightforward, note what worked well.
- **Body Reconciliation:** Only include if prose sections needed updating. Omit entirely if nothing is stale.

5. **If prose reconciliation found stale sections**, update the objective body:

```bash
erk exec update-issue-body <issue-number> --body "$(cat <<'BODY_EOF'
<full updated body text with reconciled sections>
BODY_EOF
)"
```

6. **Validate the objective:**

```bash
erk objective check <issue-number> --json-output
```

If checks fail, report failures and attempt to fix. The JSON output now includes `all_complete`.

7. **Check closing triggers using `all_complete`:**

**If `all_complete` is `true`:**

- **If `--auto-close` was provided:** Post "Action: Objective Complete" comment, close the issue (`gh issue close <issue-number>`), report: "All steps complete - objective closed automatically"
- **Otherwise:** Report back to parent: "All steps complete, user should be asked if they want to close"

**If `all_complete` is `false`:**

- Report the update is complete. Use `roadmap.next_step` to describe next focus.

### Step 2: Handle Subagent Response

If the subagent reports "all steps complete", ask the user:

```
All roadmap steps are complete. Should I close objective #<number> now?
- Yes, close with final summary
- Not yet, there may be follow-up work
- I'll close it manually later
```

If yes: post final comment and close. Otherwise: acknowledge and report complete.

---

## Output Format

- **Start:** "Updating objective #<number> after landing PR #<pr-number>"
- **After writes:** "Posted action comment and updated objective body for #<number>"
- **End:** Either "Objective #<number> closed" or "Objective updated. Next focus: [next action]"
- **Always:** Display the objective URL

---

## Error Cases

| Scenario                           | Action                                       |
| ---------------------------------- | -------------------------------------------- |
| `objective-fetch-context` fails    | Display error from JSON and stop             |
| Issue not found                    | Report error and exit                        |
| Issue has no `erk-objective` label | Warn user this may not be an objective issue |
