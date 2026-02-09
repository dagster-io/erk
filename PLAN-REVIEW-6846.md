# Optimize Tripwires for Code Review

## Context

Tripwires are "if you're about to do X, consult Y" rules defined in `docs/learned/` frontmatter. They serve two audiences:
1. **Authoring agents** — loaded via `tripwires.md` in agent context during code writing
2. **Review agents** — parsed by the `.github/reviews/tripwires.md` Claude Haiku prompt during PR review

The current system is authoring-oriented. The `action` field uses prose like "using bare subprocess.run with check=True" and the generated format is "**CRITICAL: Before {action}**". The review prompt (Step 2) asks Haiku to **derive grep patterns from this natural language** — this is the weakest link. Many tripwires have no greppable pattern at all (71 planning tripwires, ~50% of architecture tripwires).

## Three Changes

### 1. Add `pattern` field to tripwire frontmatter

Add an optional `pattern: str` field — an explicit regex for mechanical diff matching.

**Source frontmatter example (before):**
```yaml
tripwires:
  - action: "using bare subprocess.run with check=True"
    warning: "Use wrapper functions..."
```

**After:**
```yaml
tripwires:
  - action: "using bare subprocess.run with check=True"
    warning: "Use wrapper functions..."
    pattern: "subprocess\\.run\\("
```

**Files:**
- `src/erk/agent_docs/models.py` — Add `pattern: str | None` to `Tripwire` and `CollectedTripwire` dataclasses
- `src/erk/agent_docs/operations.py`:
  - `_validate_tripwires()` (line 106) — Parse `pattern` from `item_dict.get("pattern")`, validate it's a string and compiles as regex (`re.compile()`)
  - `collect_tripwires()` — Thread `pattern` through to `CollectedTripwire`

**Criteria for when a tripwire gets a `pattern`:**
- YES: The action describes identifiable code tokens (`subprocess.run`, `os.chdir`, `monkeypatch`, `Path.home()`)
- YES: A regex can match with acceptable precision (few false positives)
- NO: Architectural decisions ("choosing between exceptions and discriminated unions")
- NO: Workflow actions ("entering Plan Mode in replan workflow")
- NO: Negative patterns ("without explicit checkout" — can't grep for absence)

### 2. Embed patterns in the existing `tripwires.md` generation

Modify `generate_category_tripwires_doc()` to include patterns inline. All tripwires are present (with or without patterns). The review prompt uses patterns mechanically where available, and falls back to LLM reasoning for the rest.

**Generated format (before):**
```
**CRITICAL: Before using bare subprocess.run with check=True** → Read [Subprocess Wrappers](subprocess-wrappers.md) first. Use wrapper functions...
```

**Generated format (after — with pattern):**
```
**CRITICAL: Before using bare subprocess.run with check=True** [pattern: `subprocess\.run\(`] → Read [Subprocess Wrappers](subprocess-wrappers.md) first. Use wrapper functions...
```

**Generated format (after — without pattern, unchanged):**
```
**CRITICAL: Before choosing between exceptions and discriminated unions** → Read [Discriminated Union Error Handling](discriminated-union-error-handling.md) first. If callers branch on the error...
```

**Files:**
- `src/erk/agent_docs/operations.py`:
  - `generate_category_tripwires_doc()` (line 400) — Conditionally include `[pattern: ...]` when `tripwire.pattern is not None`
  - Add pattern coverage stats to sync output (e.g., "45 of 110 architecture tripwires have patterns")

### 3. Restructure the review prompt

Restructure the review prompt into two tiers: mechanical matching for pattern-bearing tripwires, and LLM-derived matching for the rest.

**Current flow (`.github/reviews/tripwires.md`):**
1. Load category `tripwires.md` → parse all entries
2. **Claude derives grep patterns from prose for ALL tripwires** ← unreliable, Haiku's weakest step
3. Lazy-load docs for matches → check exceptions
4. Post comments

**New flow — two tiers:**
1. Load category `tripwires.md` → separate entries into two groups:
   - **Tier 1**: Tripwires with `[pattern: ...]` — mechanical grep matching
   - **Tier 2**: Tripwires without patterns — LLM-derived matching (current behavior, but now scoped to a smaller set)
2. **Tier 1**: For each explicit pattern, grep the diff. Deterministic, no reasoning needed.
3. **Tier 2**: For remaining tripwires, derive search approach from the action text (existing behavior).
4. For all matches, lazy-load the linked doc → check exceptions (Haiku judgment).
5. Post comments.

**Key prompt changes in `.github/reviews/tripwires.md`:**

**Step 1** — Still loads `tripwires.md`, but now instructs Claude to parse tripwires into two groups based on whether `[pattern: ...]` is present.

**Step 2** — Two-tier matching:
```markdown
## Step 2: Match Tripwires to Diff

### Tier 1: Mechanical Pattern Matching
For tripwires that have an explicit `[pattern: ...]`:
1. Search the diff for lines matching the pattern regex
2. Record: pattern, file path, line number, matched text
3. Apply each pattern EXACTLY as written — do not modify or skip patterns

### Tier 2: Semantic Matching
For tripwires WITHOUT an explicit pattern:
1. Derive a search approach from the action text
2. Scan the diff for matching code constructs
3. Use your judgment — these require understanding intent, not just tokens
```

**Step 3** — Unchanged (lazy-load docs, check exceptions).

**Allowed tools** — Add `Bash(grep:*)` to `allowed_tools` in frontmatter so Claude can run grep for Tier 1 patterns mechanically.

## Implementation Sequence

1. **Schema + validation** — Add `pattern` field to models and validation. Tests.
2. **Generation** — Update `generate_category_tripwires_doc()` to include `[pattern: ...]` inline. Tests.
3. **Review prompt** — Restructure `.github/reviews/tripwires.md` with two-tier matching.
4. **Backfill patterns** — Add `pattern` fields to source frontmatter, starting with highest-signal categories (architecture, testing, cli). Can be done incrementally.

## Verification

- `erk docs sync` generates `tripwires.md` with `[pattern: ...]` annotations on pattern-bearing entries
- Non-pattern entries remain unchanged in format
- Run the review locally with `erk exec run-review --name tripwires --local` on a test branch with known violations
- Confirm Tier 1 patterns match expected code (e.g., `subprocess.run(` triggers the subprocess tripwire)
- Confirm Tier 2 tripwires are still evaluated via LLM reasoning
- Confirm the review correctly loads exception docs and doesn't false-positive on exception cases