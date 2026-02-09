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

Tripwires come in two formats:

**With explicit pattern** (Tier 1 — mechanical matching):

```
**[action text]** [pattern: `regex_here`] → Read [linked doc] first. [summary]
```

**Without pattern** (Tier 2 — semantic matching):

```
**[action text]** → Read [linked doc] first. [summary]
```

Parse EVERY tripwire entry and classify into:

- **Tier 1**: Has `[pattern: ...]` — extract the regex for mechanical grep matching
- **Tier 2**: No pattern — extract the action text for LLM-derived matching

For all tripwires, extract:

- **Action**: The action text (e.g., "calling os.chdir()", "passing dry_run boolean flags")
- **Linked doc**: The documentation file to read if triggered
- **Summary**: Brief description of what the rule enforces

## Step 2: Match Tripwires to Diff

### Tier 1: Mechanical Pattern Matching

For tripwires that have an explicit `[pattern: ...]`:

1. Use `grep` to search the diff for lines matching the pattern regex
2. Record: pattern, file path, line number, matched text
3. Apply each pattern EXACTLY as written — do not modify or skip patterns
4. This is deterministic — no reasoning needed, just mechanical regex matching

### Tier 2: Semantic Matching

For tripwires WITHOUT an explicit pattern:

1. Derive a search approach from the action text (e.g., "calling os.chdir()" → search for `os.chdir(`)
2. Convert natural language to code patterns (e.g., "importing time module" → `import time`)
3. Scan the diff for matching code constructs
4. Use your judgment — these require understanding intent, not just tokens

This is DYNAMIC - the category tripwire files are the source of truth. New tripwires added via frontmatter are automatically collected when `erk docs sync` runs.

Track which tripwires matched the diff (triggered tripwires).

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

### Tier 1 Pattern Matches
✅ `pattern` - None found
❌ `pattern` - Found in src/foo.py:12

(Mechanical grep results for pattern-bearing tripwires)

### Tier 2 Semantic Matches
✅ [action] - None found
❌ [action] - Found in src/foo.py:12

(LLM-derived matches for tripwires without patterns)

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
- "Triggered 3 tripwires (2 Tier 1, 1 Tier 2), loaded docs, found 1 violation"

Keep the last 10 log entries maximum.
