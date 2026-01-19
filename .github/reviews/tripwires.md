---
name: Tripwires Review
paths:
  - "**/*.py"
  - "**/*.sh"
  - ".claude/**/*.md"
marker: "<!-- tripwires-review -->"
model: claude-sonnet-4-5
timeout_minutes: 30
allowed_tools: "Bash(gh:*),Bash(erk exec:*),Bash(TZ=*),Read(*)"
enabled: true
---

## Step 1: Load Tripwire Index

Read `docs/learned/tripwires.md`. This is the **definitive source** of all tripwires.

Each tripwire follows this format:

```
**CRITICAL: Before [trigger action]** → Read [linked doc] first. [summary]
```

Parse EVERY tripwire entry to extract:

- **Trigger**: The action pattern (e.g., "calling os.chdir()", "passing dry_run boolean flags")
- **Linked doc**: The documentation file to read if triggered
- **Summary**: Brief description of what the rule enforces

## Step 2: Match Tripwires to Diff

For EACH tripwire parsed in Step 1, scan the diff for code matching its trigger pattern.

**Deriving search patterns from tripwires:**

Each tripwire's trigger text (e.g., "Before calling os.chdir()") tells you what to search for:

- Extract the action from the trigger (e.g., "calling os.chdir()" → search for `os.chdir(`)
- Convert natural language to code patterns (e.g., "importing time module" → `import time`)
- Look for the specific constructs mentioned (e.g., "adding a new method to Git ABC" → new method definitions in `src/erk/gateways/git/abc.py`)

This is DYNAMIC - the tripwires.md file is the single source of truth. New tripwires added there are automatically checked.

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
**Tripwire**: [pattern detected] - [why it's a problem] - [fix suggestion]
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
