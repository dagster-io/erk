---
title: Markdown Formatting in CI Workflows
read_when:
  - "editing markdown files"
  - "handling Prettier CI failures"
  - "implementing documentation changes"
tripwires:
  - action: "editing markdown files in docs/"
    warning: "Run `make prettier` via devrun after markdown edits. Multi-line edits trigger Prettier failures. Never manually format - use the command."
---

# Markdown Formatting in CI Workflows

How to handle Prettier formatting for markdown files in CI workflows.

## Table of Contents

- [Problem: Prettier Formatting Failures](#problem-prettier-formatting-failures)
- [Solution: Pre-emptive Formatting](#solution-pre-emptive-formatting)
- [Standard Workflow](#standard-workflow)
- [Anti-Patterns](#anti-patterns)

---

## Problem: Prettier Formatting Failures

### What Happens

When editing markdown files (especially multi-line changes):

1. **Edit markdown file:** Add/update content in `docs/learned/*.md`
2. **Run CI:** Execute `make fast-ci` or equivalent
3. **Prettier check fails:**
   ```
   docs/learned/planning/foo.md
     ✖ Formatting issues detected
   ```
4. **CI fails:** Workflow blocks on formatting error

### Why It Happens

Prettier enforces consistent markdown formatting:

- **Line wrapping:** Max line length (usually 80-120 chars)
- **List formatting:** Consistent indentation and spacing
- **Heading spacing:** Blank lines before/after headings
- **Code block formatting:** Consistent fencing

Manual edits often don't match Prettier's rules, especially for:

- Long paragraphs (need wrapping)
- Nested lists (complex indentation)
- Multiple consecutive edits (inconsistent spacing)

### Impact

Formatting failures block:

- CI completion
- PR readiness
- Merge to main

---

## Solution: Pre-emptive Formatting

### Pattern: Format After Edit

Always run Prettier **after** editing markdown files, **before** running CI:

```
1. Edit markdown files (Write/Edit tools)
2. Run `make prettier` via devrun
3. Run `make fast-ci` via devrun
4. Commit if CI passes
```

### Why Pre-emptive?

- **Prevents failures:** Formatting issues caught before CI
- **Saves time:** Don't wait for CI to discover formatting issues
- **Avoids manual formatting:** Prettier handles complex cases correctly

---

## Standard Workflow

### Step-by-Step

#### 1. Edit Markdown Files

Make changes using Write or Edit tools:

```markdown
# Example edit

## New Section

This is new content that might be long and exceed line length limits, causing Prettier to reformat it with proper wrapping.
```

#### 2. Format with Prettier (via devrun)

**Use devrun agent to run:**

```bash
make prettier
```

**Why devrun:** The `make prettier` command is a write operation (runs `prettier --write`), but devrun executes it as a command.

**Output:**

```
Checking formatting...
docs/learned/planning/foo.md
  ✔ Formatted
```

#### 3. Run CI Checks (via devrun)

**Use devrun agent to run:**

```bash
make fast-ci
```

Or specific check:

```bash
prettier --check docs/**/*.md
```

**Output:**

```
All matched files use Prettier code style!
```

#### 4. Commit Changes

If CI passes, commit both:

- Original markdown edits
- Prettier formatting changes

```bash
git add docs/learned/planning/foo.md
git commit -m "Add documentation for foo"
```

---

## Anti-Patterns

### ❌ Anti-Pattern 1: Manual Formatting

**Don't:**

```
I'll manually format the markdown file to match Prettier's style.

*Reads file, counts characters, manually wraps lines*
```

**Why wrong:**

- Time-consuming
- Error-prone
- Misses Prettier's nuanced rules
- May still fail Prettier check

**Correct:**

```
Use devrun agent to run: make prettier
```

### ❌ Anti-Pattern 2: Skip Formatting, Hope CI Passes

**Don't:**

```
I've edited the markdown file. Let's run CI and see if it passes.

Use devrun agent to run: make fast-ci
```

**Why wrong:**

- Likely to fail on Prettier check
- Wastes CI cycle
- Requires retry after formatting

**Correct:**

```
Use devrun agent to run: make prettier
(Then run fast-ci)
```

### ❌ Anti-Pattern 3: Edit Formatting via Edit Tool

**Don't:**

```
Prettier check failed. Let me manually wrap this line at 80 characters.

*Uses Edit tool to break long line*
```

**Why wrong:**

- Line wrapping is just one issue; Prettier checks many rules
- Manual wrapping may not match Prettier's algorithm
- Other formatting issues may remain

**Correct:**

```
Use devrun agent to run: make prettier
```

---

## Integration with Slash Commands

### `/local:fast-ci`

The fast-ci command includes Prettier checks:

1. Runs unit tests
2. Runs lint (ruff)
3. Runs format check (prettier)
4. Runs type check (ty)

**If Prettier fails during fast-ci:**

```
Use devrun agent to run: make prettier
(Then re-run fast-ci)
```

### Post-Plan-Implement Hook

If `.erk/prompt-hooks/post-plan-implement-ci.md` exists, it may include:

```markdown
1. Run `make prettier` via devrun
2. Run `make fast-ci` via devrun
3. Fix any failures iteratively
```

This ensures formatting is handled before final CI.

---

## When Prettier Changes Files

### Expected Behavior

After `make prettier`, you may see:

```
Modified: docs/learned/planning/foo.md
```

**This is normal.** Prettier reformatted the file.

### What Changed?

Common changes:

- **Line wrapping:** Long lines broken at ~80 chars
- **List spacing:** Consistent spacing in lists
- **Heading spacing:** Blank lines added before/after headings
- **Trailing spaces:** Removed
- **Final newline:** Added if missing

### Review Changes

Before committing, review Prettier's changes:

```bash
git diff docs/learned/planning/foo.md
```

Ensure:

- Content is preserved (no accidental deletions)
- Formatting improves readability
- No unexpected changes

---

## Prettier Configuration

### Config Location

**File:** `.prettierrc` or `prettier.config.js` (in project root)

**Common settings for markdown:**

```json
{
  "proseWrap": "always",
  "printWidth": 80,
  "tabWidth": 2,
  "useTabs": false
}
```

### Ignoring Files

**File:** `.prettierignore`

Files excluded from Prettier:

```
node_modules/
.erk/
.impl/
.worker-impl/
```

---

## Summary: Edit-Format-CI-Commit

| Phase     | Action                        | Tool         |
| --------- | ----------------------------- | ------------ |
| 1. Edit   | Modify markdown content       | Write/Edit   |
| 2. Format | Run `make prettier`           | devrun agent |
| 3. CI     | Run `make fast-ci`            | devrun agent |
| 4. Fix    | Fix test/lint failures if any | Parent agent |
| 5. Verify | Re-run `make fast-ci`         | devrun agent |
| 6. Commit | Commit changes                | Bash/git     |

**Key:** Always format (step 2) before CI (step 3).

---

## Related Documentation

- [CI Iteration Pattern](ci-iteration.md) - devrun delegation pattern
- [Plan Implement CI Customization](plan-implement-customization.md) - Post-implementation CI hooks
- [Formatter Tools](formatter-tools.md) - Overview of prettier, ruff, and other formatters
