# Update Claude Artifacts: Rename "step" to "node" in Objective Context

Part of Objective #7391, Node 5.1

## Context

Objective #7391 migrates all "step" terminology to "node" in the objectives system. Phases 1-4 completed the migration in source code (`src/`), tests, and the YAML schema. This final phase (5.1) updates all Claude artifacts (`.claude/` files) — skills, commands, and agent definitions — to use "node" terminology consistently.

**Important distinction:** Many `.claude/` files use "Step N:" as procedural headings for agent instructions (e.g., "### Step 1: Parse Arguments"). These are NOT objective roadmap terminology and MUST NOT be changed. Only rename "step" when it refers to an **objective roadmap step** (now "node").

## Changes

### 1. `.claude/skills/objective/SKILL.md`

**Line-by-line changes (only objective-context uses of "step"):**

- Line 103: `**Phase/Step:** 1.2` -> `**Phase/Node:** 1.2`
- Line 115: `View an objective's dependency graph, dependencies, and next step:` -> `View an objective's dependency graph, dependencies, and next node:`
- Line 127: `To implement a specific roadmap step, create an erk-plan that references the objective:` -> `To implement a specific roadmap node, create an erk-plan that references the objective:`
- Line 130: `erk plan create --title "Implement [step description]" --body "Part of Objective #123, Step 1.2"` -> `erk plan create --title "Implement [node description]" --body "Part of Objective #123, Node 1.2"`
- Line 136: `2. **Inspect progress** - View dependency graph and next step` -> `2. **Inspect progress** - View dependency graph and next node`
- Line 139: `5. **Spawn erk-plans** - For individual implementation steps` -> `5. **Spawn erk-plans** - For individual implementation nodes`
- Line 140: `6. **Close** - When goal achieved or abandoned (proactively ask when all steps done)` -> `6. **Close** - When goal achieved or abandoned (proactively ask when all nodes done)`

**DO NOT change:**
- Line 46: "Two-step for all changes" (refers to the two-step update pattern, not roadmap steps)
- Line 148: "two-step update workflow" (same — update workflow pattern)

### 2. `.claude/skills/objective/references/format.md`

**Line-by-line changes:**

- Line 100: `**Phase/Step:** 1.2` -> `**Phase/Node:** 1.2`
- Line 116: `- Step 1.2: pending -> done` -> `- Node 1.2: pending -> done`
- Line 147: `- Completing one or more roadmap steps` -> `- Completing one or more roadmap nodes`
- Line 151: `- **Adding new phases or steps**` -> `- **Adding new phases or nodes**`
- Line 159: `- Minor progress within a step` -> `- Minor progress within a node`
- Line 167: `- **Roadmap tables** - Change step statuses, add PR links (via exec commands)` -> `- **Roadmap tables** - Change node statuses, add PR links (via exec commands)`
- Line 170: `- **Step descriptions** - Adjust scope if what was built differs from what was planned` -> `- **Node descriptions** - Adjust scope if what was built differs from what was planned`
- Line 297: `**Phase/Step:** 1` -> `**Phase/Node:** 1`
- Line 313: `- Phase 1: all steps -> done` -> `- Phase 1: all nodes -> done`
- Line 321: `**Phase/Step:** 2` -> `**Phase/Node:** 2`
- Line 337: `- Phase 2: all steps -> done` -> `- Phase 2: all nodes -> done`
- Line 343: `When all steps in a phase are done:` -> `When all nodes in a phase are done:`
- Line 351: `When a step is blocked:` -> `When a node is blocked:`
- Line 363: `**Phase/Step:** 2.3` -> `**Phase/Node:** 2.3`
- Line 377: `- Step 2.3: pending -> blocked (waiting on #400)` -> `- Node 2.3: pending -> blocked (waiting on #400)`
- Line 382: Section header `### Skipping Steps` -> `### Skipping Nodes`
- Line 384: `When deciding to skip a step:` -> `When deciding to skip a node:`
- Line 388: `**Phase/Step:** 3.2` -> `**Phase/Node:** 3.2`
- Line 402: `- Step 3.2: pending -> skipped (no mutations to preview)` -> `- Node 3.2: pending -> skipped (no mutations to preview)`
- Line 407: Section header `### Splitting Steps` -> `### Splitting Nodes`
- Line 410: `## Action: Split authentication step` -> `## Action: Split authentication node`
- Line 413: `**Phase/Step:** 2.1` -> `**Phase/Node:** 2.1`
- Line 418: `- Realized authentication is complex enough to warrant separate step` -> `- Realized authentication is complex enough to warrant separate node`
- Line 427: `- Step 2.1 split into:` -> `- Node 2.1 split into:`
- Line 449: `**Phase/Step:** 2.1-6.3` -> `**Phase/Node:** 2.1-6.3`
- Line 468: `- Phase 2-6: all steps -> done (#3485)` -> `- Phase 2-6: all nodes -> done (#3485)`
- Line 474: `- Changed all Phase 2-6 step statuses from \`pending\` to \`done\`` -> `- Changed all Phase 2-6 node statuses from \`pending\` to \`done\``
- Line 475: `- Added PR #3485 link to each completed step` -> `- Added PR #3485 link to each completed node`
- Line 488: `**Phase/Step:** N/A (scope expansion)` -> `**Phase/Node:** N/A (scope expansion)`
- Line 518: `**Phase/Step:** 2.3` -> `**Phase/Node:** 2.3`
- Line 534: `- Step 2.3: blocked -> done` -> `- Node 2.3: blocked -> done`
- Line 539: `- Changed step 2.3 status from \`blocked\` to \`done\`` -> `- Changed node 2.3 status from \`blocked\` to \`done\``
- Line 570: `| \`next_step\` | object\\|null | First pending step (id, description, phase) |` -> `| \`next_step\` | object\\|null | First pending node (id, description, phase) |`
  **Note:** Keep the field name `next_step` as-is — it's a JSON API field name from the source code (already migrated or kept stable). Only change the English description.
- Line 575: `Use \`erk exec update-objective-node\` for surgical updates to a single step's Plan, PR, and Status cells.` -> `Use \`erk exec update-objective-node\` for surgical updates to a single node's Plan, PR, and Status cells.`
- Line 577: `For multi-step updates or structural changes` -> `For multi-node updates or structural changes`

**DO NOT change:**
- Line 436: "Real examples of the two-step update workflow" (refers to the two-step pattern)
- Any "### Step N:" procedural headings

### 3. `.claude/skills/objective/references/workflow.md`

**Line-by-line changes:**

- Line 39: `3. **Structure for steelthread** - Split phases into sub-phases (XA, XB, XC)` (no change)
- Line 40: `4. **Break into steps** - Specific tasks within each sub-phase` -> `4. **Break into nodes** - Specific tasks within each sub-phase`
- Line 41: `5. **Add test statements** - Each sub-phase needs "Test: [acceptance criteria]"` (no change)
- Line 93: `- Steps: \`NA.M\` numbering (e.g., 1A.1, 1A.2, 1B.1)` -> `- Nodes: \`NA.M\` numbering (e.g., 1A.1, 1A.2, 1B.1)`
- Line 97: `Objectives coordinate work; erk-plans execute it. Spawn an erk-plan for individual steps.` -> `Objectives coordinate work; erk-plans execute it. Spawn an erk-plan for individual nodes.`
- Line 103: `- A roadmap step is ready to implement` -> `- A roadmap node is ready to implement`
- Line 104: `- The step is well-defined and scoped` -> `- The node is well-defined and scoped`
- Line 109: `1. **Identify the step** - Which roadmap step to implement` -> `1. **Identify the node** - Which roadmap node to implement`
- Line 113: `# Create an erk-plan for a specific objective step` -> `# Create an erk-plan for a specific objective node`
- Line 115: `--title "[Step description]"` -> `--title "[Node description]"`
- Line 119: `Part of Objective #<issue-number>, Step <N.M>.` -> `Part of Objective #<issue-number>, Node <N.M>.`
- Line 125: `[Specific deliverable for this step]` -> `[Specific deliverable for this node]`
- Line 134: `3. **Update objective** - Mark step as in-progress` -> `3. **Update objective** - Mark node as in-progress`
- Line 140: `3. **Update objective body** - step status, link PR` -> `3. **Update objective body** - node status, link PR`
- Line 141: `4. **Check for closing** - If all steps done, see [closing.md](closing.md)` -> `4. **Check for closing** - If all nodes done, see [closing.md](closing.md)`
- Line 151: `# View dependency graph and next step` -> `# View dependency graph and next node`
- Line 166: `2. **Read recent comments** - Latest actions and lessons` (no change)
- Line 167: `3. **Check roadmap** - What steps are pending next` -> `3. **Check roadmap** - What nodes are pending next`
- Line 171: `1. **Identify next step** from roadmap` -> `1. **Identify next node** from roadmap`
- Line 173: `3. **Work on the step**` -> `3. **Work on the node**`
- Line 245: `- Completing steps (obvious)` -> `- Completing nodes (obvious)`
- Line 254: `- Update step statuses` -> `- Update node statuses`
- Line 260: `- Add detail as work progresses` (no change)
- Line 268: `- Split steps when needed, not preemptively` -> `- Split nodes when needed, not preemptively`

**DO NOT change:**
- Line 15, 234: "Two-step" pattern references (workflow pattern, not roadmap)
- Any "### Step N:" procedural headings (e.g., "### Step 1: Define the goal")
- Line 207: "Signs Your Phase Needs Splitting" section talks about generic "steps" in a phase structure sense — these refer to "steps" within a sub-phase description. Change these to "nodes": Line 200: `- Steps mix infrastructure + wiring + commands` -> `- Nodes mix infrastructure + wiring + commands`
- Line 208: `- Naming Convention` section: Line 208 "sub-phases, not sub-steps" -> "sub-phases, not sub-nodes"

### 4. `.claude/skills/objective/references/closing.md`

**Line-by-line changes:**

- Line 9: `### Trigger 1: All Steps Complete` -> `### Trigger 1: All Nodes Complete`
- Line 11: `When updating an objective and ALL roadmap steps show \`done\` or \`skipped\` status:` -> `When updating an objective and ALL roadmap nodes show \`done\` or \`skipped\` status:`
- Line 14: `All roadmap steps are complete. Should I close objective #<number> now?` -> `All roadmap nodes are complete. Should I close objective #<number> now?`
- Line 36: `After any objective update that marks the last pending step as done, proactively check:` -> `After any objective update that marks the last pending node as done, proactively check:`
- Line 38: `1. Are all steps now done/skipped?` -> `1. Are all nodes now done/skipped?`
- Line 45: `- All roadmap steps are done or explicitly skipped` -> `- All roadmap nodes are done or explicitly skipped`
- Line 57: `- [ ] All roadmap steps are \`done\` or \`skipped\` (with reasons for skipped)` -> `- [ ] All roadmap nodes are \`done\` or \`skipped\` (with reasons for skipped)`
- Line 133: `- Update issue body if needed (ensure all steps marked done)` -> `- Update issue body if needed (ensure all nodes marked done)`
- Line 137: `- All steps are done but no final summary posted` -> `- All nodes are done but no final summary posted`

**DO NOT change:**
- Line 64: "## The Two-Step Close" (workflow pattern)
- Line 66: "### Step 1: Post Final Action Comment" (procedural heading)
- Line 87: "### Step 2: Close the Issue" (procedural heading)

### 5. `.claude/skills/objective/references/updating.md`

**Line-by-line changes:**

- Line 15: `| Complete a step | "Action: Completed X" | Status -> done, add PR |` -> `| Complete a node | "Action: Completed X" | Status -> done, add PR |`

**DO NOT change:**
- Line 7, 11: "two-step" pattern references (workflow pattern)

### 6. `.claude/commands/erk/objective-plan.md`

**Line-by-line changes:**

- Line 107-108: `PENDING_STEPS:\n- 1.2: <description>` -> `PENDING_NODES:\n- 1.2: <description>`
- Line 109: `- 3.1: <description>` (no change needed, it's under the heading)
- Line 111: `RECOMMENDED: <step-id or "none">` -> `RECOMMENDED: <node-id or "none">`
- Line 122: `Only include steps with status "pending" in PENDING_STEPS section.` -> `Only include nodes with status "pending" in PENDING_NODES section.`
- Line 123: `Use the "next_step" field from check output as RECOMMENDED.` (keep `next_step` as JSON field name, no change)
- Line 138: `Then use AskUserQuestion to ask which step to plan:` -> `Then use AskUserQuestion to ask which node to plan:`
- Line 141: `Which step should I create a plan for?` -> `Which node should I create a plan for?`
- Line 142: `- Step 1A.1: <description> (Recommended)` -> `- Node 1A.1: <description> (Recommended)`
- Line 143: `- Step 1A.2: <description>` -> `- Node 1A.2: <description>`
- Line 144: `- Step 2B.1: <description> (plan in progress, #456)` -> `- Node 2B.1: <description> (plan in progress, #456)`
- Line 145: `- (Other - specify step number or description)` -> `- (Other - specify node number or description)`
- Line 142 annotation: `first pending step without plan in progress` -> `first pending node without plan in progress`
- Line 148: `Steps with status "pending"` -> `Nodes with status "pending"`
- Line 149: `Steps with status "in_progress"` -> `Nodes with status "in_progress"`
- Line 150: `Steps with status "done", "blocked", or "skipped"` -> `Nodes with status "done", "blocked", or "skipped"`
- Line 154: `Use the \`next_step\` field...as the recommended option. If \`next_step\` is null, no step is recommended.` -> `Use the \`next_step\` field...as the recommended option. If \`next_step\` is null, no node is recommended.` (keep `next_step` as JSON field name)
- Line 156: `If all steps are complete or have plans in progress` -> `If all nodes are complete or have plans in progress`
- Line 158: `All complete: "All roadmap steps are complete!..."` -> `All complete: "All roadmap nodes are complete!..."`
- Line 159: `All have plans: "All pending steps have plans in progress..."` -> `All have plans: "All pending nodes have plans in progress..."`
- Line 161: `### Step 5: Create Roadmap Step Marker` -> `### Step 5: Create Roadmap Node Marker`
- Line 163: `After the user selects a step, create a marker to store the selected step ID` -> `After the user selects a node, create a marker to store the selected node ID`
- Line 170: `Replace \`<step-id>\` with the step ID selected by the user (e.g., "2A.1"). This marker enables \`plan-save\` to automatically update the objective's roadmap table with the plan issue number.` -> `Replace \`<step-id>\` with the node ID selected by the user (e.g., "2A.1"). This marker enables \`plan-save\` to automatically update the objective's roadmap table with the plan issue number.`
- Line 177: `2. **Step context:** What the specific step requires` -> `2. **Node context:** What the specific node requires`
- Line 187: `2. Focus the plan on the specific step selected` -> `2. Focus the plan on the specific node selected`
- Line 192: `- Reference to objective: \`Part of Objective #<number>, Step <step-id>\`` -> `- Reference to objective: \`Part of Objective #<number>, Node <step-id>\``
- Line 193: `- Clear goal for this specific step` -> `- Clear goal for this specific node`
- Line 194: `- Implementation phases (typically 1-3 for a single step)` -> `- Implementation phases (typically 1-3 for a single node)`
- Line 248: `- **After selection:** "Creating plan for step <step-id>: <description>"` -> `- **After selection:** "Creating plan for node <step-id>: <description>"`
- Line 262: `Ask user to specify which step to plan` -> `Ask user to specify which node to plan`
- Line 270: `- **One step at a time:** Each plan should focus on a single roadmap step` -> `- **One node at a time:** Each plan should focus on a single roadmap node`
- Line 272: `- **Steelthread pattern:** If planning a Phase A step, focus on minimal vertical slice` -> `- **Steelthread pattern:** If planning a Phase A node, focus on minimal vertical slice`

**DO NOT change:**
- Procedural headings like "### Step 1: Parse Issue Reference" — these are agent workflow steps, not roadmap nodes

### 7. `.claude/commands/erk/objective-create.md`

**Line-by-line changes:**

- Line 296: `- Track progress by updating step status in the issue` -> `- Track progress by updating node status in the issue`

**DO NOT change:**
- Line 283: "validates the roadmap in one step" (generic English, not roadmap terminology)
- Procedural headings (Step 1-6)
- JSON `"steps"` field in `objective-render-roadmap` input — this is the **exec command's API** and NOT part of this migration scope (the exec command already handles the mapping internally)

### 8. `.claude/commands/erk/objective-update-with-landed-pr.md`

**Line-by-line changes:**

- Line 45: `roadmap.matched_steps: Step IDs where...` -> `roadmap.matched_steps: Node IDs where...`
- Line 47: `roadmap.summary: Step counts (done, pending, etc.)` -> `roadmap.summary: Node counts (done, pending, etc.)`
- Line 48: `roadmap.next_step: First pending step or null` -> `roadmap.next_step: First pending node or null` (keep `next_step` as JSON key name)
- Line 49: `roadmap.all_complete: True if every step is done or skipped` -> `roadmap.all_complete: True if every node is done or skipped`
- Line 53: `### Step 2: Update Roadmap Steps` heading -> `### Step 2: Update Roadmap Nodes`
- Line 55: `Read \`matched_steps\` from the context blob. These are the steps this plan completed` -> `Read \`matched_steps\` from the context blob. These are the nodes this plan completed`
- Line 57: `Pass ALL completed steps as multiple \`--node\` flags in ONE command. Do NOT run separate commands per step` -> `Pass ALL completed nodes as multiple \`--node\` flags in ONE command. Do NOT run separate commands per node`
- Line 59: `extract the existing plan reference for each completed step` -> `extract the existing plan reference for each completed node`
- Line 62: `--node <step-id-1> --node <step-id-2>` -> `--node <node-id-1> --node <node-id-2>`
- Line 65: `Preserve the existing plan reference for each step` -> `Preserve the existing plan reference for each node`
- Line 73: `- Read upcoming step descriptions` -> `- Read upcoming node descriptions`
- Line 79: `| **Scope change** | Step says "Add 3 methods"...| Step description in roadmap |` -> `| **Scope change** | Node says "Add 3 methods"...| Node description in roadmap |`
- Line 89: `"roadmap_updates": ["Step X.Y: status -> done"]` -> `"roadmap_updates": ["Node X.Y: status -> done"]`
- Line 102: `this step:` (generic procedural, keep as-is)
- Line 125-126: `"PR #\`<pr>\` landed successfully."` and `"This PR is part of Objective #\`<objective>\`."` (no change needed)
- Line 137: `Use \`roadmap.next_step\` to describe next focus` (keep `next_step` as JSON key, no change to key name. But the English around it: currently says `next_step` — no English description change needed here since it just references the field)
- Line 139: `- Mark relevant roadmap steps as \`done\`` -> `- Mark relevant roadmap nodes as \`done\``
- Line 142: `- Add PR number to the step` -> `- Add PR number to the node`
- Line 145: `3. Check if all steps are complete` -> `3. Check if all nodes are complete`

**DO NOT change:**
- Procedural headings (### Step 1, ### Step 3, etc.)
- `phase_step` JSON key (it's a source code API field)
- Line 109: "skip this step entirely" (procedural)

### 9. `.claude/commands/erk/objective-list.md`

**Line-by-line changes:**

- Line 35: `- \`/erk:objective-plan <number>\` -- Create a plan for the next step` -> `- \`/erk:objective-plan <number>\` -- Create a plan for the next node`

### 10. `.claude/commands/local/objective-view.md`

**Line-by-line changes:**

- Line 156: `<done_nodes>/<total_nodes> steps completed` -> `<done_nodes>/<total_nodes> nodes completed`
- Line 192: `- \`/erk:objective-plan <number>\` - Create a plan for the next pending node` (already says "node" - verify, no change needed)

### 11. `.claude/commands/erk/plan-save.md`

**Line-by-line changes:**

- Line 102: `Update the objective's roadmap table to show that a plan has been created for this step:` -> `Update the objective's roadmap table to show that a plan has been created for this node:`
- Line 104: `1. **Read the roadmap step marker** to get the step ID:` -> `1. **Read the roadmap node marker** to get the node ID:`
- Line 110: `skip this step - the plan wasn't created via \`objective-plan\`.` (procedural "step", keep as-is)
- Line 122: `Display: \`Updated objective #<objective-issue> roadmap: step <step_id> -> plan #<issue_number>\`` -> `Display: \`Updated objective #<objective-issue> roadmap: node <step_id> -> plan #<issue_number>\``

### 12. `.claude/commands/erk/land.md`

**Line-by-line changes:**

- Line 139: `- Mark relevant roadmap steps as \`done\`` -> `- Mark relevant roadmap nodes as \`done\``
- Line 142: `- Add PR number to the step` -> `- Add PR number to the node`
- Line 145: `3. Check if all steps are complete - if so, offer to close the objective.` -> `3. Check if all nodes are complete - if so, offer to close the objective.`

### 13. `.claude/commands/erk/replan.md`

No changes needed. The "step" mentions in this file refer to procedural steps in the agent workflow or generic implementation steps in plans, not objective roadmap steps.

### 14. `.claude/commands/local/interview.md`

No changes needed. The "Next step:" mentions are generic procedural suggestions, not roadmap terminology.

## Files NOT Changing

The following files were checked and do NOT need changes:

- **`.claude/skills/erk-planning/SKILL.md`** and **`references/workflow.md`** — "step" refers to plan steps, not objective nodes
- **`.claude/skills/erk-exec/reference.md`** — no "step" mentions
- **`.claude/commands/erk/one-shot-plan.md`** — "Step N:" procedural headings only
- **`.claude/commands/erk/replan.md`** — generic plan/investigation steps only
- **`.claude/commands/local/interview.md`** — "Next step:" is generic
- **`.claude/commands/erk/fix-conflicts.md`** — procedural steps only
- **`.claude/commands/erk/git-pr-push.md`** — procedural steps only
- **`.claude/hooks/`** — no objective "step" references
- **`.claude/settings.json`** — no step references
- **`.claude/agents/`** — no objective "step" references in any agent definition
- **JSON field names** like `next_step`, `matched_steps`, `phase_step`, `total_steps` — these are source code API identifiers that were either already migrated in Phases 2-4 or intentionally kept stable. Do NOT rename JSON keys in command documentation.
- **`objective-render-roadmap` JSON input** — the `"steps"` key in the JSON input format is the exec command's API, handled internally. Not in scope for this PR.

## Implementation Details

### Key Discrimination Rule

The word "step" appears in two distinct contexts in `.claude/` files:

1. **Procedural agent instructions** — "### Step 1: Parse Arguments", "skip this step", "proceed to Step 6". These use "step" as a numbered instruction and must NOT be changed.

2. **Objective roadmap terminology** — "roadmap step", "Step 1.2", "Phase/Step: 2.3", "all steps done", "next step", "pending steps". These refer to objective roadmap entries and MUST be changed to "node".

**Heuristic for disambiguation:**
- If preceded by `###` and followed by a colon + description -> procedural (keep)
- If preceded by "Phase/" -> roadmap terminology (change to "Node")
- If in a roadmap table or roadmap update context -> roadmap terminology (change)
- If describing "this step" in a procedural context like "skip this step" -> procedural (keep)
- If describing a "two-step" workflow -> process pattern (keep)

### Pattern: `Phase/Step` -> `Phase/Node`

This pattern appears in action comment templates throughout the objective skill. Every instance should be changed.

### Pattern: `Step X.Y: status -> status` in Roadmap Updates

These appear in action comment examples showing roadmap status transitions. Every instance should be changed to `Node X.Y: status -> status`.

### JSON API Fields

Do NOT rename these JSON fields — they are source code identifiers:
- `next_step` (field name in CLI JSON output)
- `matched_steps` (field name in objective-fetch-context output)
- `phase_step` (field name in action comment JSON input)
- `total_steps` / `PENDING_STEPS` section header in task agent prompts — the section header `PENDING_STEPS` in the objective-plan command's task agent prompt IS a display label and SHOULD be renamed to `PENDING_NODES`

## Verification

1. **Run grep to confirm no remaining "step" in roadmap context:**
   ```bash
   # Search for remaining roadmap-step patterns
   grep -rn "Phase/Step" .claude/
   grep -rn "roadmap step" .claude/
   grep -rn "roadmap steps" .claude/
   grep -rn "Step [0-9]" .claude/skills/objective/ .claude/commands/erk/objective-*.md .claude/commands/local/objective-view.md
   ```

   These should return no matches after the changes.

2. **Run grep to confirm procedural steps are preserved:**
   ```bash
   grep -rn "### Step [0-9]" .claude/commands/ .claude/skills/
   ```

   These should still have matches (procedural headings preserved).

3. **Run ruff/prettier** on any affected files if applicable (these are markdown files, so prettier is the relevant formatter):
   ```bash
   prettier --check .claude/skills/objective/**/*.md .claude/commands/erk/objective-*.md .claude/commands/local/objective-view.md .claude/commands/erk/land.md .claude/commands/erk/plan-save.md
   ```