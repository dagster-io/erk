---
description: Extract plan from conversation, fully enhance it, and save to disk
---

# /erk:save-context-enriched-plan

⚠️ **CRITICAL: This command ONLY saves the plan - it does NOT create worktrees or implement code!**

## Goal

**Extract an implementation plan from conversation, enhance it for autonomous execution, and save it to disk.**

This command extracts a plan from conversation context, optionally applies guidance, interactively enhances it through clarifying questions, and saves it to the repository root as a markdown file.

**What this command does:**

- ✅ Find plan in conversation
- ✅ Apply optional guidance to plan
- ✅ Interactively enhance plan for autonomous execution
- ✅ Extract semantic understanding and context
- ✅ Structure complex plans into phases (when beneficial)
- ✅ Save enhanced plan to disk

**What happens AFTER (in separate commands):**

- ⏭️ Create worktree: `/erk:create-wt-from-plan-file`
- ⏭️ Navigate and implement: `erk checkout <branch> && claude --permission-mode acceptEdits "/erk:implement-plan"`

## What Happens

When you run this command, these steps occur:

1. **Verify Scope** - Confirm we're in a git repository
2. **Detect Plan** - Search conversation for implementation plan
   3-5. **Enrichment Process** - Apply guidance, extract understanding, and enhance interactively
3. **Generate Filename** - Derive filename from plan title
4. **Detect Root** - Find repository root directory
5. **Save Plan** - Write enhanced plan to disk as markdown file

## Usage

```bash
/erk:save-context-enriched-plan [guidance]
```

**Examples:**

- `/erk:save-context-enriched-plan` - Save enhanced plan to disk
- `/erk:save-context-enriched-plan "Make error handling more robust and add retry logic"` - Apply guidance to plan
- `/erk:save-context-enriched-plan "Fix: Use LBYL instead of try/except throughout"` - Apply corrections to plan

## Prerequisites

- An implementation plan must exist in conversation
- Current working directory must be in a git repository
- (Optional) Guidance text for final corrections/additions to the plan

## Semantic Understanding & Context Preservation

**Why This Matters:** Planning agents often discover valuable insights that would be expensive for implementing agents to re-derive. Capturing this context saves time and prevents errors.

**What to Capture:**

1. **API/Tool Quirks**
   - Undocumented behaviors, race conditions, timing issues
   - Example: "Stripe webhooks can arrive before API response returns"
   - Include: Why it matters, how to handle, what to watch for

2. **Architectural Insights**
   - WHY code is structured certain ways (not just how)
   - Design boundaries and their rationale
   - Example: "Config split across files due to circular imports"

3. **Domain Logic & Business Rules**
   - Non-obvious invariants, edge cases, compliance requirements
   - Example: "Never delete audit records, only mark as archived"
   - Include: Rationale, validation criteria, edge cases

4. **Complex Reasoning**
   - Alternatives considered and rejected with reasons
   - Dependencies between choices
   - Example: "Can't use async here because parent caller is sync"

5. **Known Pitfalls**
   - Anti-patterns that seem right but cause problems
   - Framework-specific gotchas
   - Example: "Don't use .resolve() before checking .exists()"

6. **Raw Discoveries Log**
   - Everything discovered during planning, even if minor
   - Examples: Version numbers, config formats, conventions observed

7. **Planning Artifacts**
   - Code snippets examined, commands run, configurations discovered
   - Example: "Checked auth.py lines 45-67 for validation pattern"

8. **Implementation Risks**
   - Technical debt, uncertainties, performance concerns, security considerations
   - Example: "No caching layer could cause issues at scale"

**Inclusion Philosophy:** Cast a wide net - over-document rather than under-document. Include anything that:

- Took ANY time to discover (even 30 seconds of research)
- MIGHT influence implementation decisions
- Could POSSIBLY cause bugs or confusion
- Wasn't immediately obvious on first glance
- Required any clarification or discussion
- Involved ANY decision between alternatives
- Required looking at documentation or examples

**Remember:** It's easier for implementing agents to skip irrelevant context than to rediscover missing context. When in doubt, include it.

**How It's Used:** This understanding gets captured in the "Context & Understanding" section of enhanced plans, linked to specific implementation steps.

## Success Criteria

This command succeeds when ALL of the following are true:

**Plan Extraction:**
✅ Implementation plan extracted from conversation context
✅ If guidance provided, it has been applied to the plan
✅ Semantic understanding extracted and integrated

**File Creation:**
✅ Plan saved to `<repo-root>/<filename>-plan.md`
✅ File is valid markdown and contains enhanced content

**Output:**
✅ JSON output provided with file path and status
✅ Next steps clearly communicated to user

## Troubleshooting

### "No plan found in context"

**Cause:** Plan not in conversation or doesn't match detection patterns
**Solution:**

- Ensure plan is in conversation history
- Plan should have headers like "## Implementation Plan" or numbered steps
- Re-paste plan in conversation if needed

### "Plan file already exists"

**Cause:** File with same name exists at repository root
**Solution:**

- Change plan title to generate different filename
- Delete existing file: `rm <repo-root>/<filename>-plan.md`

### Enhancement suggestions not applied correctly

**Cause:** Ambiguous user responses or misinterpretation
**Solution:**

- Be specific in responses to clarifying questions
- Use clear action words: "Fix:", "Add:", "Change:", "Reorder:"

---

## Agent Instructions

You are executing the `/erk:save-context-enriched-plan` command. Follow these steps carefully:

---

🔴 **CRITICAL: YOU ARE ONLY WRITING MARKDOWN - DO NOT IMPLEMENT**

- DO NOT use Edit or Write tools except for the final plan file
- DO NOT implement any code from the plan
- DO NOT modify any files in the codebase
- ONLY save ONE markdown file at `<repo-root>/<name>-plan.md`

---

### Step 0: Verify Scope and Constraints

🔴 **REMINDER: YOU ARE ONLY WRITING MARKDOWN**

- DO NOT use Edit or Write tools except for the final plan file
- DO NOT implement any code from the plan
- DO NOT modify any files in the codebase
- ONLY save ONE markdown file at `<repo-root>/<name>-plan.md`

**Error Handling Template:**
All errors must follow this format:

```
❌ Error: [Brief description in 5-10 words]

Details: [Specific error message, relevant context, or diagnostic info]

Suggested action: [1-3 concrete steps to resolve]
```

**YOUR ONLY TASKS:**

1. Extract implementation plan from conversation
2. Apply guidance modifications if provided
3. Extract semantic understanding from planning discussion
4. Interactively enhance plan for autonomous execution
5. Save enhanced plan to disk as markdown file
6. Provide JSON output with file path

**FORBIDDEN ACTIONS:**

- Writing ANY code files (.py, .ts, .js, etc.)
- Making ANY edits to existing codebase
- Creating ANY worktrees
- Running ANY commands except `git rev-parse`
- Implementing ANY part of the plan

**ALLOWED TOOLS ONLY:**

- ✅ Read (to examine conversation context)
- ✅ AskUserQuestion (for clarification)
- ✅ Bash (ONLY `git rev-parse --show-toplevel`)
- ✅ Write (ONLY for final plan file at `<repo-root>/*-plan.md`)

**IF YOU USE:** Edit, Write (to codebase files), Bash (other commands), Task, NotebookEdit, SlashCommand, etc.
→ 🔴 **YOU ARE IMPLEMENTING, NOT PLANNING. STOP IMMEDIATELY.**

This command only saves the plan. Worktree creation happens via `/erk:create-wt-from-plan-file`.

### Step 1: Detect Implementation Plan in Context

🔴 **REMINDER: YOU ARE ONLY WRITING MARKDOWN**

- DO NOT use Edit or Write tools except for the final plan file
- DO NOT implement any code from the plan
- DO NOT modify any files in the codebase
- ONLY save ONE markdown file at `<repo-root>/<name>-plan.md`

Search conversation history for an implementation plan:

**Search strategy:**

1. Work backwards from most recent messages
2. Stop at first complete plan found
3. Look for markdown content with structure

**What constitutes a complete plan:**

- Minimum 100 characters
- Contains headers (# or ##) OR numbered lists OR bulleted lists
- Has title/overview AND implementation steps

**Common plan patterns:**

- Markdown with "Implementation Plan:", "Overview", "Implementation Steps"
- Structured task lists or step-by-step instructions
- Headers containing "Plan", "Tasks", "Steps", "Implementation"

**If no plan found:**

```
❌ Error: No implementation plan found in conversation

Details: Could not find a valid implementation plan in conversation history

Suggested action:
  1. Ensure plan is in conversation
  2. Plan should have headers and structure
  3. Re-paste plan in conversation if needed
```

**Plan validation:**

- Must be at least 100 characters
- Must contain structure (numbered lists, bulleted lists, or multiple headers)
- If invalid, show error:

```
❌ Error: Plan content is too minimal or invalid

Details: Plan lacks structure or implementation details

Suggested action:
  1. Provide a more detailed implementation plan
  2. Include specific tasks, steps, or phases
  3. Use headers and lists to structure the plan
```

### Steps 2-4: Enrichment Process

@../docs/enrichment-process.md

Apply the complete enrichment process to enhance the extracted plan for autonomous execution. This includes:

- Step 1: Apply optional guidance (if provided as command argument)
- Step 2: Extract semantic understanding from planning discussion
- Step 3: Interactive enhancement with clarifying questions

[Continue with Step 5: Generate Filename from Plan...]

### Step 5: Generate Filename from Plan

🔴 **REMINDER: YOU ARE ONLY WRITING MARKDOWN**

- DO NOT use Edit or Write tools except for the final plan file
- DO NOT implement any code from the plan
- DO NOT modify any files in the codebase
- ONLY save ONE markdown file at `<repo-root>/<filename>`

**Title Extraction (LLM semantic analysis):**

1. **Try H1 header** - Look for `# Title` at start of document
2. **Try H2 header** - Look for `## Title` if no H1
3. **Try prefix patterns** - Look for text after "Plan:", "Implementation Plan:", "Feature Plan:"
4. **Fallback to first line** - Use first non-empty line as last resort

**Filename Transformation (Kit CLI):**

Use the kit CLI command to transform the extracted title to a filename:

```bash
filename=$(dot-agent kit-command erk issue-title-to-filename "$extracted_title")
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to generate filename" >&2
    exit 1
fi
```

The kit CLI command handles:

- Lowercase conversion
- Unicode normalization (NFD decomposition)
- Emoji and special character removal
- Hyphen collapse and trimming
- Validation of at least one alphanumeric character
- Returns "plan.md" if title is empty after cleanup
- Appends `-plan.md` suffix automatically

**No length restriction:** DO NOT truncate the base name. The base name is limited to 30 characters by `sanitize_worktree_name()` during worktree creation, but filename generation does NOT truncate.

**If title extraction fails:**

```
❌ Error: Could not extract title from plan

Details: Plan has no headers or first line

Suggested action:
  1. Add a clear title to your plan (e.g., # Feature Name)
  2. Or provide a name: What would you like to name this plan?
```

Use AskUserQuestion tool to get the plan title from the user if extraction fails.

**Example transformations:**

- "User Authentication System" → `user-authentication-system-plan.md`
- "Version-Specific Dignified Python Kits Structure" → `version-specific-dignified-python-kits-structure-plan.md`
- "Fix: Database Connection Issues" → `fix-database-connection-issues-plan.md`
- "🚀 Awesome Feature!!!" → `awesome-feature-plan.md`
- "café Feature" → `cafe-feature-plan.md`
- "测试 Feature" → `feature-plan.md`

### Step 6: Detect Repository Root

🔴 **REMINDER: YOU ARE ONLY WRITING MARKDOWN**

- DO NOT use Edit or Write tools except for the final plan file
- DO NOT implement any code from the plan
- DO NOT modify any files in the codebase
- ONLY save ONE markdown file at `<repo-root>/<name>-plan.md`

Execute: `git rev-parse --show-toplevel`

This returns the absolute path to the root of the current repository. Store this as `<repo-root>` for use in subsequent steps.

**If the command fails:**

```
❌ Error: Could not detect repository root

Details: Not in a git repository or git command failed

Suggested action:
  1. Ensure you are in a valid git repository
  2. Run: git status (to verify git is working)
  3. Check if .git directory exists
```

### Step 6.5: Verify You Did Not Implement

🔴 **CRITICAL: VERIFY YOU ONLY GATHERED INFORMATION**

Before saving the plan, confirm you ONLY gathered information and did NOT implement anything.

**Check your tool usage in this session:**

- ✅ Did you use Read to examine conversation? → CORRECT
- ✅ Did you use AskUserQuestion for clarifications? → CORRECT
- ✅ Did you use Bash(git rev-parse) to find repo root? → CORRECT
- ❌ Did you use Edit on ANY file? → **VIOLATION - STOP**
- ❌ Did you use Write on ANY codebase file (not plan)? → **VIOLATION - STOP**
- ❌ Did you use Task, SlashCommand, or other tools? → **VIOLATION - STOP**
- ❌ Did you run ANY bash commands besides git rev-parse? → **VIOLATION - STOP**

**If you violated restrictions:**

```
❌ Error: Implementation attempted during plan persistence

Details: You used [tool name] which is forbidden in /erk:save-context-enriched-plan

This command ONLY writes markdown. Implementation happens in /erk:implement-plan.

Suggested action:
  1. Stop immediately - do NOT save the plan
  2. Report what tools you used incorrectly
  3. User should restart the command without implementing
```

**If all checks passed:** Proceed to Step 7 to save the plan.

### Step 7: Save Plan to Disk

🔴 **REMINDER: YOU ARE ONLY WRITING MARKDOWN**

- DO NOT use Edit or Write tools except for the final plan file
- DO NOT implement any code from the plan
- DO NOT modify any files in the codebase
- ONLY save ONE markdown file at `<repo-root>/<filename>`

**Note:** The `filename` from Step 5 already includes the `-plan.md` suffix (generated by kit CLI command). No need to append it again.

**Add enrichment marker:**

Before saving the plan content, prepend YAML front matter to mark it as enriched:

```markdown
---
erk_plan: true
---

[plan content here]
```

This marker enables detection of erk plans for status display in both `erk status` and Claude Code status line.

**If filename base validation fails:**

```
❌ Error: Internal error - filename base exceeds 30 characters

Details: Generated base name '<base>' is <length> characters (max: 30)

This is a bug in the filename generation algorithm. The base should have been
truncated to 30 characters in Step 5.

Suggested action:
  1. Report this as a bug in /erk:save-context-enriched-plan
  2. Manually truncate the plan title and rerun the command
```

**If file already exists:**

```
❌ Error: Plan file already exists

Details: File exists at: <repo-root>/<derived-filename>

Suggested action:
  1. Change plan title to generate different filename
  2. Or delete existing: rm <repo-root>/<derived-filename>
  3. Or choose different plan name
```

**Save the plan:**

Use the Write tool to save:

- Path: `<repo-root>/<derived-filename>`
- Content: Full enhanced plan markdown content
- Verify file creation

**If save fails:**

```
❌ Error: Failed to save plan file

Details: [specific write error from tool]

Suggested action:
  1. Check file permissions in repository root
  2. Verify available disk space
  3. Ensure path is valid: <repo-root>/<derived-filename>
```

**Output success message:**

```markdown
✅ Plan saved: <repo-root>/<derived-filename>

You can now:

1. Review and edit the plan file if needed
2. Create GitHub issue: /erk:create-plan-issue-from-plan-file
3. Implement with unified command: erk implement #<issue_number>

Alternative (file-based workflow):

- Create worktree directly: /erk:create-wt-from-plan-file

---

{"plan_file": "<repo-root>/<derived-filename>", "status": "created"}
```

## Important Notes

- 🔴 **This command does NOT create worktrees** - only saves enhanced plan
- Searches conversation for implementation plans
- Enhances plans through clarifying questions when helpful
- Suggests phase decomposition for complex plans with multiple features
- All enhancements are optional - users can dismiss suggestions
- Filename derived from plan title, prompts user if extraction fails
- All errors follow consistent template with details and suggested actions
- User can edit the plan file after creation before creating worktree
- Always provide clear feedback at each step
