---
title: Skill-Based Commit Message Generation
read_when:
  - "creating commits for significant changes"
  - "preparing PR submissions"
  - "using /erk:git-pr-push command"
---

# Skill-Based Commit Message Generation

Pattern of loading diff analysis skills before committing for better commit messages.

## Table of Contents

- [Why Skill-Generated Messages](#why-skill-generated-messages)
- [Pattern: Load Skill → Analyze → Generate → Commit](#pattern-load-skill--analyze--generate--commit)
- [Comparison: Hand-Written vs. Skill-Generated](#comparison-hand-written-vs-skill-generated)
- [Reference: /erk:git-pr-push](#reference-erkgit-pr-push)

---

## Why Skill-Generated Messages

### Hand-Written Commit Messages

When writing commit messages manually:

- **Generic:** "Update documentation"
- **Missing context:** Doesn't explain why
- **Incomplete:** Doesn't capture all changes
- **Inconsistent:** Style varies across commits

### Skill-Generated Commit Messages

Skills analyze diffs and generate messages that are:

- **Strategic:** Captures overall goal
- **Component-aware:** Identifies affected subsystems
- **Comprehensive:** Includes all significant changes
- **Consistent:** Follows project conventions

### Example Comparison

**Hand-written:**

```
Add context preservation documentation
```

**Skill-generated:**

```
Add Context Preservation Prompting to Replan Workflow

Introduced Steps 6a-6b to prevent sparse plans in replan consolidation.
Gather investigation context explicitly before plan mode entry.

Changes:
- planning/: context-preservation-in-replan.md, context-preservation-patterns.md
- sessions/: lifecycle.md
- cli/: pr-operations.md
- ci/: ci-iteration.md, markdown-formatting.md

Closes #6172
```

**Difference:**

- Skill message explains **why** (prevent sparse plans)
- Lists **all affected areas** (planning, sessions, cli, ci)
- Includes **issue reference** (Closes #6172)
- Provides **context** (Steps 6a-6b rationale)

---

## Pattern: Load Skill → Analyze → Generate → Commit

### Four-Step Process

#### 1. Load Skill

Before analyzing changes, load the diff analysis skill:

```
Load erk-diff-analysis skill
```

**Why:** Skill provides:

- Diff parsing expertise
- Component identification
- Commit message templates
- Strategic summarization

#### 2. Analyze Changes

Let skill analyze the current diff:

```
Analyze staged changes for commit message
```

**Skill examines:**

- Which files changed
- What components are affected
- Why changes were made (from file content)
- What issue is being addressed

#### 3. Generate Message

Skill produces commit message:

```
Title: Add Context Preservation Prompting to Replan Workflow

Body:
Introduced Steps 6a-6b to prevent sparse plans in replan consolidation.
...
```

#### 4. Commit

Use generated message:

```bash
git commit -m "$(cat <<'EOF'
Add Context Preservation Prompting to Replan Workflow

Introduced Steps 6a-6b to prevent sparse plans...

Closes #6172
EOF
)"
```

---

## Comparison: Hand-Written vs. Skill-Generated

### Scenario: Documentation Update

**Staged changes:**

```
docs/learned/planning/context-preservation-in-replan.md (new)
docs/learned/planning/context-preservation-patterns.md (new)
docs/learned/planning/lifecycle.md (modified)
docs/learned/sessions/lifecycle.md (new)
docs/learned/cli/pr-operations.md (new)
```

### Hand-Written Message

```
Add documentation for context preservation

Added several documentation files for the replan workflow.
```

**Problems:**

- Doesn't list what was added
- Doesn't explain why
- Doesn't mention affected areas

### Skill-Generated Message

```
Add Context Preservation Documentation for Replan Workflow

Documented the Steps 6a-6b pattern introduced in PR #6167 to prevent sparse
plans during replan consolidation. Created comprehensive guides for context
preservation patterns, prompting structures, and verification checklists.

Documentation added:
- planning/context-preservation-in-replan.md - Problem, solution, Step 6a-6b walkthrough
- planning/context-preservation-patterns.md - Anti-patterns vs. correct patterns
- planning/context-preservation-prompting.md - Prompt structures for eliciting context
- checklists/investigation-findings.md - Pre-plan-mode verification checklist
- sessions/lifecycle.md - Session file persistence and availability
- cli/pr-operations.md - Duplicate PR prevention patterns

Updated:
- planning/lifecycle.md - Added plan-header metadata completeness section

This documentation ensures future agents understand context preservation
requirements and avoid creating sparse plans.

Closes #6172
```

**Advantages:**

- ✅ Explains **why** (prevent sparse plans)
- ✅ Lists **all files** with descriptions
- ✅ Provides **context** (PR #6167 connection)
- ✅ Includes **impact** (future agents benefit)
- ✅ Links **issue** (Closes #6172)

---

## Reference: /erk:git-pr-push

The `/erk:git-pr-push` command uses this pattern automatically.

### Command Overview

**Location:** `.claude/commands/erk/git-pr-push.md`

**Purpose:** Pure git workflow for PR submission

### Workflow Steps

1. **Check for existing PR** (prevents duplicates)
2. **Load erk-diff-analysis skill**
3. **Analyze staged changes**
4. **Generate commit message** (skill-based)
5. **Create commit** with generated message
6. **Push to remote**
7. **Create or update PR**

### Skill Loading in Command

From `/erk:git-pr-push` Step 2:

```markdown
### Step 2: Load Diff Analysis Skill

Load the `erk-diff-analysis` skill:

Use Skill tool to load: erk-diff-analysis

This skill provides commit message generation based on diff analysis.
```

### Message Generation in Command

From `/erk:git-pr-push` Step 4:

```markdown
### Step 4: Generate Commit Message

Use the loaded skill to analyze staged changes and generate commit message:

1. Analyze git diff
2. Identify changed components
3. Generate strategic commit message
4. Include "Closes #N" if issue is linked
```

---

## When to Use Skill-Based Messages

### Always Use for:

- **Feature implementations:** Multi-file changes, significant functionality
- **Documentation updates:** Multiple new/updated docs
- **Refactoring:** Structural changes across components
- **Bug fixes:** Non-trivial fixes affecting multiple areas

### Optional for:

- **Typo fixes:** Single-line changes to fix typos
- **Formatting:** Auto-generated formatting changes only
- **Config tweaks:** Minor configuration adjustments

### Never Use for:

- **Empty commits:** CI trigger commits with `--allow-empty`
- **Merge commits:** Git-generated merge messages
- **Revert commits:** Git-generated revert messages

---

## Integration with PR Body

### PR Body Generation

After commit, the PR body is generated from the commit message:

```bash
gh pr create --title "$COMMIT_TITLE" --body "$(cat <<EOF
$COMMIT_BODY

## Test Plan
- [ ] CI passes
- [ ] Manual verification

---
$PR_FOOTER
EOF
)"
```

**Where:**

- `$COMMIT_TITLE` = First line of commit message
- `$COMMIT_BODY` = Rest of commit message
- `$PR_FOOTER` = Standardized footer with checkout instructions

### PR Body Format

```markdown
Add Context Preservation Documentation for Replan Workflow

Documented the Steps 6a-6b pattern introduced in PR #6167...

[Full commit message body]

## Test Plan

- [ ] CI passes
- [ ] Manual verification

---

## Checkout Instructions

\`\`\`bash
gh pr checkout <PR_NUMBER>
\`\`\`
```

---

## Skill Loading Best Practices

### Load Once per Session

Skills persist for the session, so load once:

```
# First commit
Load erk-diff-analysis skill
[Generate message and commit]

# Second commit (same session)
[Skill already loaded, just generate and commit]
```

### Verify Skill is Loaded

Check conversation history for:

```
The "erk-diff-analysis" skill is loading...
```

If present, skill is loaded and available.

---

## Summary

| Aspect              | Hand-Written          | Skill-Generated            |
| ------------------- | --------------------- | -------------------------- |
| Style               | Generic               | Strategic, component-aware |
| Completeness        | Often incomplete      | Comprehensive              |
| Context             | Missing "why"         | Includes rationale         |
| Issue linking       | Often forgotten       | Automatic (Closes #N)      |
| PR body integration | Manual                | Automatic                  |
| Consistency         | Varies                | Project conventions        |
| Time investment     | Quick but low quality | Automated, high quality    |
| Tool support        | Manual writing        | Skill analyzes diff        |
| Component awareness | Manual identification | Automatic detection        |
| Strategic framing   | Generic "update X"    | "Add X to enable Y for Z"  |

**Recommendation:** Always load `erk-diff-analysis` skill before committing significant changes.

---

## Related Documentation

- [PR Submission Workflow](../cli/pr-submission.md) - Full git-only PR submission pattern
- [Git-PR-Push Command](../../../.claude/commands/erk/git-pr-push.md) - Reference implementation
- [Diff Analysis Skill](../../../.claude/skills/erk-diff-analysis/) - Skill specification
