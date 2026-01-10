# Documentation Extraction Plan

## Objective

Document the .worker-impl/ cleanup mechanism and related patterns discovered while investigating PR #4531.

## Source Information

- Session ID: 34990eb6-16e3-4091-95cd-54d97a8aff05
- Context: Bug investigation for orphaned .worker-impl/ in PRs

## Documentation Items

### Item 1: Update impl-folder-lifecycle.md with Cleanup Mechanism

**Type:** Category A (Learning Gap)
**Location:** docs/learned/architecture/impl-folder-lifecycle.md
**Action:** Update existing document
**Priority:** High

**Content to add:**

Add a new section "## Cleanup Mechanism" after "## Why Two Folders?":

```markdown
## Cleanup Mechanism

The `.worker-impl/` folder must be removed before the final PR submission. There are two code paths:

### GitHub Actions Workflow (`erk-impl.yml`)

Lines 187-190 handle cleanup after implementation:

```bash
if [ -d .worker-impl/ ]; then
  git rm -rf .worker-impl/
  echo "Staged .worker-impl/ removal for commit"
fi
```

**CRITICAL:** Must use `git rm -rf` not `rm -rf`. Filesystem deletion (`rm`) doesn't stage the change in git, so the folder remains in the commit tree.

### Local Implementation (`impl-execute.md`)

Step 13 of the impl-execute command includes explicit cleanup after CI passes:

```bash
if [ -d .worker-impl/ ]; then
  git rm -rf .worker-impl/
  git commit -m "Remove .worker-impl/ after implementation"
  git push
fi
```

### Common Pitfall

Using `rm -rf .worker-impl/` (filesystem only) instead of `git rm -rf .worker-impl/` causes the folder to remain in the PR even though it's deleted locally. The deletion must be staged and committed.
```

---

### Item 2: Add Tripwire for Git-Staged Deletion

**Type:** Category B (Teaching Gap)  
**Location:** docs/learned/tripwires.md (via frontmatter)
**Action:** Add new tripwire
**Priority:** Medium

**Content:**

Add to the appropriate source file's frontmatter:

```yaml
tripwires:
  - trigger: "Before using rm -rf on a committed directory that needs to be removed in a commit"
    action: "Use git rm -rf instead. Filesystem deletion (rm) doesn't stage the change - the directory remains in git's index and will still appear in commits."
```

---

### Item 3: Document Slash Command Explicitness Pattern

**Type:** Category B (Teaching Gap)
**Location:** docs/learned/commands/index.md or new file docs/learned/commands/explicitness.md
**Action:** Add guidance
**Priority:** Low

**Content:**

```markdown
## Command Explicitness

When writing Claude slash commands, prefer explicit bash code blocks over prose instructions.

### Why

Prose instructions like "delete folder, commit cleanup, push" may be:
- Misinterpreted by Claude
- Skipped if Claude loses track of steps
- Executed incorrectly (e.g., using `rm` instead of `git rm`)

### Pattern

**Avoid:**
```markdown
After CI passes:
- Delete .worker-impl/ folder
- Commit the cleanup
- Push to remote
```

**Prefer:**
```markdown
After CI passes, clean up .worker-impl/ if present:

\`\`\`bash
if [ -d .worker-impl/ ]; then
  git rm -rf .worker-impl/
  git commit -m "Remove .worker-impl/ after implementation"
  git push
fi
\`\`\`
```

Explicit code blocks are executed more reliably and prevent implementation errors.
```

## Verification

After implementing:
1. Run `erk docs sync` to regenerate tripwires.md
2. Verify the new content appears in the appropriate files
3. Check that tripwire shows in `docs/learned/tripwires.md`