---
name: Tripwires Review
paths:
  - "**/*.py"
  - "**/*.sh"
  - ".claude/**/*.md"
marker: "<!-- tripwires-review -->"
model: claude-sonnet-4-5
timeout_minutes: 15
allowed_tools: "Bash(gh:*),Bash(erk exec:*),Bash(TZ=*),Bash(grep:*),Read(*)"
enabled: true
---

## Step 1: Run Mechanical Scan

Run: `erk exec tripwire-scan --base origin/main`

Parse the JSON output. The scan:

- Determines which tripwire categories apply to the changed files
- Runs all Tier 1 regex patterns mechanically against added lines in the diff
- Returns compact JSON with Tier 1 results and Tier 2 entries

If the scan fails (success=false), fall back to the manual process:
read category tripwire files based on the diff and grep patterns manually.

## Step 2: Evaluate Tier 1 Matches

For each entry in `tier1_matches`:

1. Read the linked doc at the `doc_path` (relative to `docs/learned/<category>/`)
2. Extract ALL rules AND EXCEPTIONS from that doc
3. Check if any exceptions apply to the matched code
4. Only flag as a violation if NO exception applies

If `tier1_matches` is empty, skip this step.

**CRITICAL: Read the full doc to understand exceptions.**

Many rules have explicit exceptions. For example, the "5+ parameters" rule has exceptions for:

- ABC/Protocol method signatures
- Click command callbacks (Click injects parameters positionally)

If the code matches an exception, it is NOT a violation. Do not flag it.

**You MUST load and read the linked documentation before deciding if something is a violation.** The tripwire summary is abbreviated - the full exceptions are only in the linked docs.

## Step 3: Evaluate Tier 2 Entries

For each entry in `tier2_entries`:

1. Derive a search approach from the action text (e.g., "calling os.chdir()" -> search for `os.chdir(`)
2. Convert natural language to code patterns (e.g., "importing time module" -> `import time`)
3. Scan the diff for matching code constructs
4. If triggered, read the linked doc and check exceptions
5. Flag violations only when no exception applies

Use your judgment - these require understanding intent, not just tokens.

## Step 4: Inline Comment Format

When posting inline comments for violations, use this format:

```
**Tripwire**: [pattern detected] - [which tripwire/doc triggered]
```

## Step 5: Summary Comment Format

Summary format (preserve existing Activity Log entries and prepend new entry):

```
### Tripwires Triggered
- [tripwire name] -> loaded [doc path]
- [tripwire name] -> loaded [doc path]

(List only tripwires that matched the diff)

### Tier 1 Pattern Matches
(From mechanical scan JSON - tier1_matches and tier1_clean)
x `pattern` - Found in src/foo.py:12
v `pattern` - None found

### Tier 2 Semantic Matches
x [action] - Found in src/foo.py:12
v [action] - None found

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
