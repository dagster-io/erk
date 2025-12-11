---
description: Create worktree from existing plan file on disk
---

# /create-planned-wt

⚠️ **CRITICAL: This command ONLY creates the worktree - it does NOT implement code!**

## Goal

**Create a erk worktree from an existing plan file on disk.**

This command detects plan files at the repository root, selects the most recent one, creates a worktree with that plan, and displays next steps.

**What this command does:**

- ✅ Auto-detect most recent `*-plan.md` file at repo root
- ✅ Create worktree with `erk create --plan`
- ✅ Display plan content from disk (including any manual edits)

**What happens AFTER (in separate command):**

- ⏭️ Navigate and implement: `erk checkout <branch> && claude --permission-mode acceptEdits "/erk:implement-plan"`

## What Happens

When you run this command, these steps occur:

1. **Verify Scope** - Confirm we're in a git repository with erk available
2. **Detect Plan File** - Find and select most recent `*-plan.md` at repo root
3. **Read Plan Content** - Read plan file before it gets moved by erk
4. **Create Worktree** - Run `erk create --plan` command
5. **Display Next Steps** - Show plan content and implementation command

## Usage

```bash
/create-planned-wt
```

**No arguments accepted** - This command automatically detects and uses the most recent plan file.

## Prerequisites

- At least one `*-plan.md` file must exist at repository root
- Current working directory must be in a git repository
- Typically run after `/persist-plan` (optionally with manual edits to plan file)

## Success Criteria

This command succeeds when ALL of the following are true:

**Plan Detection:**
✅ Plan file detected at repository root
✅ Most recent plan file selected (if multiple exist)

**Worktree Creation:**
✅ Worktree created with `erk create --plan`
✅ Worktree contains `.plan/` folder with `plan.md` and `progress.md`
✅ Worktree listed in `erk list`

**Next Steps:**
✅ Plan content displayed (including user edits)
✅ Next command displayed: `erk checkout <branch> && claude --permission-mode acceptEdits "/erk:implement-plan"`

## Troubleshooting

### "No plan files found"

**Cause:** No `*-plan.md` files exist at repository root
**Solution:**

- Run `/persist-plan` to create a plan first
- Ensure plan file ends with `-plan.md`
- Verify you're in the correct repository

### "Invalid plan file"

**Cause:** Plan file exists but is unreadable or empty
**Solution:**

- Check file permissions: `ls -la <plan-file>`
- Verify file content: `cat <plan-file>`
- Re-run `/persist-plan` if file is corrupted

### "Worktree already exists"

**Cause:** Worktree with derived name already exists
**Solution:**

- List worktrees: `erk list`
- Delete existing: `erk delete <name>`
- Or navigate to existing: `erk checkout <branch>`

### "Failed to parse erk output"

**Cause:** Erk version doesn't support --json flag
**Solution:**

- Check version: `erk --version`
- Update: `uv tool upgrade erk`

---

## Agent Instructions

You are executing the `/create-planned-wt` command. Follow these steps carefully:

### Step 0: Verify Scope and Constraints

**Error Handling Template:**
All errors must follow this format:

```
❌ Error: [Brief description in 5-10 words]

Details: [Specific error message, relevant context, or diagnostic info]

Suggested action: [1-3 concrete steps to resolve]
```

**YOUR ONLY TASKS:**

1. Detect plan file at repository root
2. Validate plan file (exists, readable, not empty)
3. Read plan content from disk (BEFORE it gets moved)
4. Run `erk create --plan <file>`
5. Display plan content and next steps

**FORBIDDEN ACTIONS:**

- Writing ANY code files (.py, .ts, .js, etc.)
- Making ANY edits to existing codebase
- Running ANY commands except `git rev-parse` and `erk create`
- Implementing ANY part of the plan
- Modifying the plan file

This command creates the workspace. Implementation happens in the worktree via `/erk:implement-plan`.

### Step 1: Detect and Validate Plan File

**Auto-detection algorithm:**

1. Execute `git rev-parse --show-toplevel` to get repo root
2. Find all `*-plan.md` files at repo root: `list(Path(root).glob("*-plan.md"))`
3. If no files found → error (direct user to /persist-plan)
4. If files found → select most recent by modification time
5. Silently use selected file (no output about which was chosen)

**Selection code pattern:**

```python
plan_files = list(repo_root.glob("*-plan.md"))
if not plan_files:
    error("No plan files found")
most_recent = max(plan_files, key=lambda p: p.stat().st_mtime)
```

**Minimal validation:**

- Check file exists: `if not plan_path.exists()`
- Check file readable: Try to read first byte
- Check not empty: `plan_path.stat().st_size > 0`
- No structure validation required

**Error if no plans found:**

```
❌ Error: No plan files found in repository root

Details: No *-plan.md files exist at <repo-root>

Suggested action:
  1. Run /persist-plan to create a plan first
  2. Ensure the plan file ends with -plan.md
```

**Error if validation fails:**

```
❌ Error: Invalid plan file

Details: File at <path> [does not exist / is not readable / is empty]

Suggested action:
  1. Verify file exists: ls -la <path>
  2. Check file permissions
  3. Re-run /persist-plan if needed
```

**Error if git command fails:**

```
❌ Error: Could not detect repository root

Details: Not in a git repository or git command failed

Suggested action:
  1. Ensure you are in a valid git repository
  2. Run: git status (to verify git is working)
  3. Check if .git directory exists
```

### Step 2: Read Plan Content (Before It Gets Moved)

**IMPORTANT:** Read the plan content NOW, before running `erk create`, because erk will move the file from the repository root to the new worktree.

Read the plan file: `plan_content = Path(plan_file_path).read_text(encoding="utf-8")`

Store this content for display in Step 4.

### Step 3: Create Worktree with Plan

Execute: `erk create --plan <plan-file-path> --json --stay`

**Parse JSON output:**

Expected JSON structure:

```json
{
  "worktree_name": "feature-name",
  "worktree_path": "/path/to/worktree",
  "branch_name": "feature-branch",
  "plan_file": "/path/to/.plan",
  "status": "created"
}
```

**Validate all required fields exist:**

- `worktree_name` (string, non-empty)
- `worktree_path` (string, valid path)
- `branch_name` (string, non-empty)
- `plan_file` (string, path to .plan folder)
- `status` (string: "created" or "exists")

**Handle errors:**

**Missing fields in JSON:**

```
❌ Error: Invalid erk output - missing required fields

Details: Missing: [list of missing fields]

Suggested action:
  1. Check erk version: erk --version
  2. Update if needed: uv pip install --upgrade erk
  3. Report issue if version is current
```

**JSON parsing fails:**

```
❌ Error: Failed to parse erk create output

Details: [parse error message]

Suggested action:
  1. Check erk version: erk --version
  2. Ensure --json flag is supported (v0.2.0+)
  3. Try running manually: erk create --plan <file> --json
```

**Worktree already exists (status = "exists"):**

```
❌ Error: Worktree already exists: <worktree_name>

Details: A worktree with this name already exists from a previous plan

Suggested action:
  1. View existing: erk status <worktree_name>
  2. Navigate to it: erk checkout <branch>
  3. Or delete it: erk delete <worktree_name>
  4. Or modify plan title to generate different name
```

**Command execution fails:**

```
❌ Error: Failed to create worktree

Details: [erk error message from stderr]

Suggested action:
  1. Check git repository health: git fsck
  2. Verify erk is installed: erk --version
  3. Check plan file exists: ls -la <plan-file>
```

**CRITICAL: Claude Code Directory Behavior**

🔴 **Claude Code CANNOT switch directories.** After `erk create` runs, you will remain in your original directory. This is **NORMAL and EXPECTED**. The JSON output gives you all the information you need about the new worktree.

**Do NOT:**

- ❌ Try to verify with `git branch --show-current` (shows the OLD branch)
- ❌ Try to `cd` to the new worktree (will just reset back)
- ❌ Run any commands assuming you're in the new worktree

**Use the JSON output directly** for all worktree information.

### Step 4: Display Next Steps

After successful worktree creation, **you MUST output the following formatted display**:

**Display format:**

```markdown
✅ Worktree created: **<worktree-name>**

Plan:

<full-plan-content-from-disk>

Branch: `<branch-name>`
Location: `<worktree-path>`

**Next step:**

`erk checkout <branch-name> && claude --permission-mode acceptEdits "/erk:implement-plan"`
```

**CRITICAL:** You MUST output this complete formatted message. Do not skip the plan content or the command.

**Template Variable Clarification:**

- `<full-plan-content-from-disk>` refers to the plan markdown read from disk in Step 2
- Output the complete plan text verbatim (all headers, sections, steps)
- This is the file content that was read BEFORE being moved by erk
- Preserve all markdown formatting (headers, lists, code blocks)
- Do not truncate or summarize the plan

**Note:** The final output the user sees should be the single copy-pasteable command above. No additional text after that command.

## Important Notes

- 🔴 **This command does NOT write code** - only creates workspace with plan
- 🔴 **This command does NOT enhance plans** - expects plan already enhanced via `/persist-plan`
- Auto-detects most recent `*-plan.md` file at repository root
- Reads plan content from disk to show any manual edits
- All errors follow consistent template with details and suggested actions
- This command does NOT switch directories or execute the plan
- User must manually run `erk checkout` and `/erk:implement-plan` to begin implementation
- The `--permission-mode acceptEdits` flag is included to automatically accept edits during implementation
- Always provide clear feedback at each step
