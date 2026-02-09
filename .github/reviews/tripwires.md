---
name: Tripwires Review
paths:
  - "**/*.py"
  - "**/*.sh"
  - ".claude/**/*.md"
marker: "<!-- tripwires-review -->"
model: claude-sonnet-4-5
timeout_minutes: 30
allowed_tools: "Bash(gh:*),Bash(erk exec:*),Bash(TZ=*),Bash(grep:*),Read(*)"
enabled: true
---

## Step 1: Load Tripwire Index

Tripwires are organized by category. Universal tripwires are in `AGENTS.md`. Category-specific tripwires are in `docs/learned/<category>/tripwires.md` (e.g., `docs/learned/architecture/tripwires.md`, `docs/learned/cli/tripwires.md`).

For comprehensive coverage, read these category tripwire files based on the diff:

- Changes in `src/erk/gateway/` or `packages/erk-shared/src/*/gateway/` → Read `docs/learned/architecture/tripwires.md`
- Changes in `src/erk/cli/` → Read `docs/learned/cli/tripwires.md`
- Changes in `tests/` → Read `docs/learned/testing/tripwires.md`
- Changes in `.github/` → Read `docs/learned/ci/tripwires.md`
- Changes in `src/erk/tui/` → Read `docs/learned/tui/tripwires.md`
- Planning-related changes → Read `docs/learned/planning/tripwires.md`

Tripwires have two formats:

**With explicit pattern:**

```
**[trigger action]** [pattern: `regex`] → Read [linked doc] first. [summary]
```

**Without pattern (semantic matching):**

```
**[trigger action]** → Read [linked doc] first. [summary]
```

Parse EVERY tripwire entry to extract:

- **Trigger**: The action pattern (e.g., "calling os.chdir()", "passing dry_run boolean flags")
- **Pattern**: Optional explicit regex for mechanical matching (e.g., `subprocess\.run\(`)
- **Linked doc**: The documentation file to read if triggered
- **Summary**: Brief description of what the rule enforces

Separate tripwires into two groups:

- **Tier 1**: Tripwires WITH `[pattern: ...]` — use mechanical regex matching
- **Tier 2**: Tripwires WITHOUT patterns — use semantic LLM-based matching

## Step 2: Match Tripwires to Diff

### Tier 1: Mechanical Pattern Matching

For tripwires WITH an explicit `[pattern: ...]`:

1. Use grep with the exact regex pattern to search the diff
2. Apply each pattern EXACTLY as written — do not modify or skip patterns
3. Record matches: pattern, file path, line number, matched text
4. This is deterministic — no reasoning needed, just pattern matching

Example:

```bash
# For pattern: subprocess\.run\(
grep -n 'subprocess\.run(' path/to/file.py
```

### Tier 2: Semantic Matching

For tripwires WITHOUT an explicit pattern:

1. Read the action text to understand what to look for
2. Derive a search approach from the action text (existing behavior)
3. Scan the diff for matching code constructs
4. Use your judgment — these require understanding intent, not just tokens

Example action: "choosing between exceptions and discriminated unions" requires analyzing architectural decisions, not just searching for keywords.

This is DYNAMIC - the category tripwire files are the source of truth. New tripwires added via frontmatter are automatically collected when `erk docs sync` runs.

Track which tripwires matched the diff (triggered tripwires) from BOTH tiers.

## Step 3: Load Docs for Matched Tripwires (Lazy Loading)

For EACH tripwire that matched in Step 2:

1. Read the linked documentation file
2. Extract ALL rules AND EXCEPTIONS from that doc
3. Check if any exceptions apply to the code being reviewed
4. Only flag as a violation if NO exception applies

**CRITICAL: Read the full doc to understand exceptions.**

Many rules have explicit exceptions. For example, the "5+ parameters" rule has exceptions for:

- ABC/Protocol method signatures
- Click command callbacks (Click injects parameters positionally)

If the code matches an exception, it is NOT a violation. Do not flag it.

**You MUST load and read the linked documentation before deciding if something is a violation.** The tripwire summary in tripwires.md is abbreviated - the full exceptions are only in the linked docs.

## Step 4: Inline Comment Format

When posting inline comments for violations, use this format:

```
**Tripwire**: [pattern detected] - [which tripwire/doc triggered]
```

## Step 5: Summary Comment Format

Summary format (preserve existing Activity Log entries and prepend new entry):

```
### Tripwires Triggered
- [tripwire name] → loaded [doc path]
- [tripwire name] → loaded [doc path]

(List only tripwires that matched the diff)

### Patterns Checked
✅ [pattern] - None found
❌ [pattern] - Found in src/foo.py:12

(Use ✅ when compliant, ❌ when violation found. Only list patterns relevant to the diff.)

### Violations Summary
- `file.py:123`: [brief description]

### Files Reviewed
- `file.py`: N violations
- `file.sh`: N violations
```

Activity log entry examples:

- "Found 2 violations (bare subprocess.run in x.py, /tmp/ usage in y.py)"
- "All violations resolved"
- "No tripwire violations detected"
- "Triggered 3 tripwires, loaded docs, found 1 violation"

Keep the last 10 log entries maximum.
