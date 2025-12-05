# Extraction Plan: PR Validation Documentation

## Objective

Add documentation for the new PR validation command, workflow integration patterns, and step numbering conventions discovered during the implementation of `erk pr check`.

## Source Information

- **Session ID**: 67b8bf5a-ae2f-4a36-8be6-29a1d2bf69c9
- **Branch**: 2251-add-erk-pr-check-command-e-12-05-1142
- **Context**: Implementation of `erk pr check` command and integration into PR submission workflows

## Documentation Items

### 1. PR Validation Command Reference (Category B - Teaching Gap)

**Location**: `docs/agent/cli/pr-commands.md` (new file or add to existing)
**Action**: Add
**Priority**: High (documents actively used feature)

**Content**:

```markdown
## erk pr check

Validates that the current branch's PR meets project standards.

### Usage

```bash
erk pr check
```

### Validations Performed

1. **Issue Closing Reference**: When `.impl/issue.json` exists, verifies PR body contains `Closes #N` (case-insensitive)
2. **Checkout Footer**: Verifies PR body contains `erk pr checkout {pr_number}`

### Output

```
Checking PR #123 for branch feature-xyz...

[PASS] PR body contains issue closing reference (Closes #456)
[PASS] PR body contains checkout footer

All checks passed
```

### Integration

This command is automatically called by:
- `/gt:pr-submit` - After PR creation
- `/gt:pr-update` - After PR update
- `/git:pr-push` - After PR creation
- `/erk:plan-implement` - After PR creation (for worker-impl flows)
```

---

### 2. Slash Command Step Numbering Convention (Category A - Learning Gap)

**Location**: `docs/agent/commands/slash-command-conventions.md` or `docs/agent/conventions.md`
**Action**: Add section
**Priority**: Medium (prevents future refactoring)

**Content**:

```markdown
## Step Numbering in Slash Commands

**Rule**: Always use whole-number steps in slash command documentation.

### Correct

```markdown
### Step 1: Do first thing
### Step 2: Do second thing
### Step 3: Do third thing
```

### Incorrect

```markdown
### Step 1: Do first thing
### Step 1.5: Do inserted thing  # ❌ Don't use fractional steps
### Step 2: Do second thing
```

### Why

- Fractional steps (1.5, 2.5) indicate steps were inserted without renumbering
- Makes commands harder to reference ("run step 3" vs "run step 2.5")
- Creates maintenance burden when steps need to be added/removed
- When adding steps, renumber all subsequent steps to maintain whole numbers
```

---

### 3. PR Workflow Integration Pattern (Category A - Learning Gap)

**Location**: `docs/agent/architecture/workflow-integration.md` (new file)
**Action**: Create
**Priority**: Low (useful but not urgent)

**Content**:

```markdown
## Adding Validation Steps to PR Workflows

When creating a new validation or hook that should run during PR submission, integrate it into all relevant workflows:

### Workflows to Update

1. **`/gt:pr-submit`** - Graphite-based PR submission
   - Location: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/commands/gt/pr-submit.md`
   - Add step after PR finalization, before results reporting

2. **`/gt:pr-update`** - Graphite PR update
   - Location: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/commands/gt/pr-update.md`
   - Add step after update workflow completes

3. **`/git:pr-push`** - Standard git PR creation
   - Location: `.claude/commands/git/pr-push.md`
   - Add step after `gh pr create`, before results reporting

4. **`/erk:plan-implement`** - Implementation workflow
   - Location: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/plan-implement.md`
   - Add step after PR creation (only for worker-impl flows)

### Pattern

```markdown
### Step N: Validate PR Rules

Run the PR check command to validate the PR:

\`\`\`bash
erk pr check
\`\`\`

This validates:
- [List what the check validates]

If any checks fail, display the output and warn the user.
```

### Non-Blocking Behavior

PR validation steps should be non-blocking by default:
- Display warnings if checks fail
- Continue to next step (results reporting)
- Let user decide whether to fix issues
```