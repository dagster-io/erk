---
description: Audit an objective against current codebase and propose updates
---

# /local:objective-reevaluate

Audits an open objective against the current codebase state, identifies stale references, already-done work, and outdated prose, then proposes and applies updates with user confirmation.

## Usage

```bash
/local:objective-reevaluate <issue-number>
```

---

## Agent Instructions

### Phase 1: Validate Input and Fetch Objective Context

Parse `$ARGUMENTS` for the issue number. If no issue number provided:

```
Error: Issue number required.
Usage: /local:objective-reevaluate <issue_number>
```

Fetch the full objective context:

```bash
erk exec objective-fetch-context --objective <NUMBER>
```

Parse the JSON output to get:

- `objective.body`: Full issue body text
- `objective.title`: Issue title
- `objective.state`: OPEN or CLOSED
- `objective.labels`: Labels list
- `roadmap.phases`: Serialized roadmap phases with node statuses, descriptions, and metadata

Verify the issue has the `erk-objective` label. If not:

```
Error: Issue #<number> is not an erk-objective issue (missing erk-objective label).
```

If the objective is CLOSED, warn:

```
Warning: Objective #<number> is CLOSED. Proceeding with audit anyway.
```

### Phase 2: Extract Auditable References

Systematically extract concrete references from the objective body that can be verified against the codebase. Build a checklist of items to audit.

**From roadmap node descriptions:**

- File paths (e.g., `src/erk/foo.py`, `tests/test_bar.py`)
- Command names (e.g., `erk inspect`, `/local:some-command`, `erk exec script-name`)
- Function/class/module names mentioned as implementation targets
- CLI subcommand references

**From Implementation Context section:**

- Key Files list entries
- Architecture descriptions referencing specific modules or patterns
- Technology or library references

**From Design Decisions section:**

- Pattern references (e.g., "uses the gateway ABC pattern")
- Technology choices that may have changed

**From pending node descriptions:**

- Descriptions of work that may already be done via other PRs

Build a structured checklist:

```
Reference Type | Source Location | Reference Value | Verification Method
file_path      | Node 1.4 desc  | src/erk/foo.py  | Glob for existence
command        | Node 2.1 desc  | erk inspect     | Grep for CLI registration
function       | Key Files       | do_thing()      | Grep for definition
pending_work   | Node 3.2       | "Add caching"   | Search for implementation
```

### Phase 3: Verify References Against Codebase

For each reference in the checklist, verify it against the current codebase:

**File paths:** Check existence via Glob tool.

**Command names:**

- For CLI commands (`erk <cmd>`): Search for Click command registration in `src/erk/cli/`
- For slash commands (`/local:<cmd>` or `/erk:<cmd>`): Check `.claude/commands/` for the file
- For exec scripts (`erk exec <script>`): Check `src/erk/cli/commands/exec/scripts/` for the file

**Function/class names:** Search via Grep in `src/erk/` for definitions.

**Pending node work:** For each pending node, search the codebase for evidence the work was already accomplished:

- Search for key terms from the node description
- Check git log for related merged PRs:
  ```bash
  gh pr list --state merged --search "<keywords from node description>" --json number,title,mergedAt --limit 5
  ```

Classify each reference:

| Status  | Meaning                                                   |
| ------- | --------------------------------------------------------- |
| CURRENT | Reference is accurate, exists as described                |
| STALE   | Reference points to something renamed, moved, or deleted  |
| DONE    | Pending node whose work was accomplished elsewhere        |
| UNCLEAR | Cannot determine status automatically, needs human review |

### Phase 4: Build Findings Report

Present a structured findings table to the user:

```markdown
## Reevaluation Findings for Objective #<number>

### Summary

- **References audited:** <total>
- **Current (no action needed):** <count>
- **Stale (needs update):** <count>
- **Done elsewhere (node completed):** <count>
- **Unclear (needs review):** <count>

### Findings

| Location             | Reference                    | Status  | Finding                                          |
| -------------------- | ---------------------------- | ------- | ------------------------------------------------ |
| Node 1.4 description | `inspect` command            | STALE   | Command merged into `view` (PR #7385)            |
| Key Files            | `src/erk/inspect_cmd.py`     | STALE   | File deleted, now `src/erk/cli/commands/view.py` |
| Node 2.3             | pending: "Add caching layer" | DONE    | Implemented in PR #7401                          |
| Node 3.1             | pending: "Refactor gateway"  | CURRENT | No evidence of implementation                    |
| Design Decisions     | "Uses polling for updates"   | UNCLEAR | Found both polling and WebSocket code            |
```

If all references are CURRENT:

```
All references are current. No updates needed for objective #<number>.
```

Stop here (skip Phases 5-6).

### Phase 5: Propose Updates

For each non-CURRENT finding, propose a specific update:

**For STALE references:**

- Propose the exact text replacement (old text -> new text)
- Identify which section of the objective body needs editing
- If a command was renamed, find the new name

**For DONE nodes:**

- Propose changing the node status to `done`
- Include evidence (PR number, commit, or code location)
- Propose adding a `pr` reference to the node metadata

**For UNCLEAR items:**

- Present the ambiguity and ask the user to decide

Format proposals as a numbered list:

```markdown
### Proposed Updates

1. **[STALE] Node 1.4 description**: Replace `inspect` with `view`
   - Old: "Run `erk inspect` to examine the objective"
   - New: "Run `erk objective view` to examine the objective"

2. **[STALE] Key Files**: Update file path
   - Old: `src/erk/inspect_cmd.py`
   - New: `src/erk/cli/commands/view.py`

3. **[DONE] Node 2.3**: Mark as done
   - Evidence: PR #7401 implemented the caching layer
   - Action: Set status to `done`, add `pr: "#7401"`

4. **[UNCLEAR] Design Decisions**: Polling vs WebSocket
   - Found both patterns in codebase. Which is the current approach?
```

### Phase 6: Execute Updates (with confirmation)

Use AskUserQuestion to let the user approve, reject, or modify proposals:

```
I've identified <N> proposed updates for objective #<number>. Would you like me to:
1. Apply all proposed updates
2. Let me pick which ones to apply
3. Skip all updates (just informational)
```

**If user approves (all or selected):**

**For DONE nodes** — update node status via exec script.

> **CRITICAL: `--plan` is required when `--pr` is set.** The CLI rejects `--pr` without `--plan` (see `docs/learned/objectives/plan-reference-preservation.md`). For each DONE node, check its current `plan` field from the Phase 1 roadmap data:
>
> - If the node already has a `plan` reference in the roadmap YAML, pass `--plan "#<existing-plan>"` to preserve it
> - If the node has no plan reference, pass `--plan ""` to explicitly indicate no plan
> - **Never omit `--plan` when `--pr` is set** — the CLI will reject it

```bash
erk exec update-objective-node <objective-number> --node <node-id> --status done --pr "#<pr-number>" --plan "#<existing-plan-or-empty>" --include-body
```

Pass all completed nodes as multiple `--node` flags in ONE command if multiple nodes are being marked done.

**For STALE references and outdated prose** — update the objective body:

After all node status updates, if prose changes are needed:

1. Use the `updated_body` from the last `update-objective-node` call (if one was made with `--include-body`), OR fetch the current body:
   ```bash
   erk exec get-issue-body <objective-number>
   ```
2. Apply the approved text replacements to the body
3. Write the updated body:
   ```bash
   erk exec update-issue-body <objective-number> --body-file /tmp/updated-objective-body.md
   ```
   (Write the updated body to a temp file first via Write tool to avoid shell quoting issues)

**Post an action comment** summarizing what was reconciled:

```bash
echo '<json>' | erk exec objective-post-action-comment
```

With JSON structure:

```json
{
  "issue_number": <N>,
  "date": "<YYYY-MM-DD>",
  "pr_number": null,
  "phase_step": "<affected node IDs, comma-separated>",
  "title": "Objective reevaluation",
  "what_was_done": ["Audited objective against current codebase", "Updated stale references: ...", "Marked nodes as done: ..."],
  "lessons_learned": ["<any insights discovered>"],
  "roadmap_updates": ["Node X.Y: pending -> done", ...],
  "body_reconciliation": [{"section": "Node 1.4 description", "change": "Updated inspect -> view"}]
}
```

Set `pr_number` to `null` (or `0`) since this is an audit action, not a PR landing.

**Report completion:**

```
Reevaluation complete for objective #<number>:
- <N> stale references updated
- <N> nodes marked as done
- <N> items flagged for manual review
- Action comment posted

View objective: <objective URL>
```

---

## Error Handling

- **Issue not found:** Display "Error: Issue #<number> not found." and stop.
- **Not an objective:** Display label requirement error and stop.
- **GitHub API rate limited:** Display "Error: GitHub API rate limited. Try again later." and stop.
- **No references found to audit:** Report "No auditable references found in objective body" and stop.
- **Exec script failure:** Display the error JSON and continue with remaining updates if possible.

## Notes

- This is a judgment-heavy skill: interpreting whether a reference is stale requires codebase understanding. Use Grep and Glob liberally.
- Never auto-mutate. Always present findings and get user approval before making changes.
- Updates both the issue body (prose/metadata) AND node statuses (via exec scripts).
- For `pr_number` in the action comment: use `null` or `0` when the reevaluation is not tied to a specific PR.
- Reuses existing exec scripts: `objective-fetch-context`, `update-objective-node`, `update-issue-body`, `get-issue-body`, `objective-post-action-comment`.
