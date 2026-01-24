# Plan: Phase 2B - Tripwire Candidate Detection

**Part of Objective #5503, Phase 2B**

## Goal

Automatically identify tripwire-worthy insights during the learn workflow and mark them with `[TRIPWIRE-CANDIDATE]` tags for easy promotion.

## Context

The learn workflow already extracts:
- **Prevention insights** (error patterns, failed approaches) via SessionAnalyzer (Phase 2A)
- **Tripwire suggestions** via DocumentationGapIdentifier

Phase 2B adds **automated detection heuristics** to identify which insights deserve tripwire status, rather than relying on manual judgment.

## Roadmap Steps

| Step | Description | Approach |
|------|-------------|----------|
| 2B.1 | Add tripwire-worthiness heuristics | Add criteria to DocumentationGapIdentifier |
| 2B.2 | Mark candidates with `[TRIPWIRE-CANDIDATE]` tag | PlanSynthesizer formatting |
| 2B.3 | Document tripwire-worthy criteria | Add to docs/learned/ |

## Design Decisions

### Where to Add Heuristics

**Decision**: Add tripwire-worthiness scoring to **DocumentationGapIdentifier** (not SessionAnalyzer).

**Rationale**:
- SessionAnalyzer extracts raw findings per session
- DocumentationGapIdentifier already classifies items (NEW_DOC, UPDATE_EXISTING, TRIPWIRE, SKIP)
- It already has priority scoring (HIGH/MEDIUM/LOW)
- Adding worthiness heuristics here keeps classification logic centralized

### Heuristic Criteria

Based on analysis of existing tripwires in `docs/learned/tripwires.md`:

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Non-obvious** | HIGH | Error/behavior not deducible from code alone |
| **Cross-cutting** | HIGH | Applies to multiple commands/areas |
| **Destructive potential** | HIGH | Could cause data loss, broken state, or wasted effort |
| **Repeated pattern** | MEDIUM | Same mistake made 2+ times in sessions |
| **External dependency** | MEDIUM | Involves external tool quirks (gh, gt, GitHub API) |
| **Silent failure** | HIGH | Error doesn't throw exception, just produces wrong result |

### Tripwire-Worthiness Score

Items with **2+ HIGH criteria** or **1 HIGH + 2 MEDIUM** → `[TRIPWIRE-CANDIDATE]`

## Implementation

### Step 1: Update DocumentationGapIdentifier Agent

**File**: `.claude/agents/learn/documentation-gap-identifier.md`

Add new section for tripwire-worthiness scoring:

```markdown
### Step 5.5: Score Tripwire Worthiness

For each item classified as TRIPWIRE or prevention insight with HIGH severity:

**Tripwire-Worthiness Criteria:**
| Criterion | Score | Check |
|-----------|-------|-------|
| Non-obvious | +2 | Error requires context to understand (not clear from code/docs) |
| Cross-cutting | +2 | Applies to 2+ commands or multiple areas |
| Destructive potential | +2 | Could cause data loss, invalid state, or significant rework |
| Silent failure | +2 | No exception thrown; wrong result produced silently |
| Repeated pattern | +1 | Same mistake appears 2+ times in sessions |
| External tool quirk | +1 | Involves gh, gt, GitHub API, or other external tool |

**Scoring:**
- Score >= 4 → Mark as `[TRIPWIRE-CANDIDATE]`
- Score 2-3 → Include in "Potential Tripwires" section
- Score < 2 → Regular documentation item
```

Update output format to include:

```markdown
## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

| # | Item | Score | Criteria Met | Suggested Trigger |
|---|------|-------|--------------|-------------------|
| 1 | Missing --no-interactive | 6 | Non-obvious, Cross-cutting, Silent failure | "Before calling gt commands without --no-interactive" |
```

### Step 2: Update PlanSynthesizer Agent

**File**: `.claude/agents/learn/plan-synthesizer.md`

Update to format tripwire candidates with the tag:

```markdown
### Step 4.5: Format Tripwire Candidates

For items marked as tripwire candidates in gap analysis:

1. Add `[TRIPWIRE-CANDIDATE]` prefix to item title
2. Include scoring breakdown
3. Format as ready-to-add tripwire entry

**Output format:**

## Tripwire Candidates

### [TRIPWIRE-CANDIDATE] 1. Missing --no-interactive flag

**Score:** 6/6 (Non-obvious +2, Cross-cutting +2, Silent failure +2)

**Trigger:** Before calling gt commands without --no-interactive flag
**Warning:** Always use `--no-interactive` with gt commands. Without it, gt may prompt for input and hang.
**Target doc:** docs/learned/architecture/git-graphite-quirks.md

**Frontmatter addition:**
```yaml
tripwires:
  - action: "calling gt commands without --no-interactive flag"
    warning: "Always use `--no-interactive` with gt commands (gt sync, gt submit, gt restack, etc.). Without this flag, gt may prompt for user input and hang indefinitely."
```
```

### Step 3: Document Criteria

**File**: `docs/learned/planning/tripwire-worthiness-criteria.md`

Create documentation explaining what makes something tripwire-worthy for human reviewers and future agents.

## Files to Modify

| File | Change |
|------|--------|
| `.claude/agents/learn/documentation-gap-identifier.md` | Add tripwire-worthiness scoring section |
| `.claude/agents/learn/plan-synthesizer.md` | Add `[TRIPWIRE-CANDIDATE]` formatting |
| `docs/learned/planning/tripwire-worthiness-criteria.md` | NEW - criteria documentation |
| `docs/learned/index.md` | Will auto-update via `erk docs sync` |

## Verification

1. **Run learn on a plan with known tripwire-worthy content**:
   ```bash
   /erk:learn <issue-with-errors>
   ```

2. **Check gap analysis output** for tripwire scoring:
   ```bash
   cat .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/gap-analysis.md
   ```
   Verify items have scores and `[TRIPWIRE-CANDIDATE]` markers

3. **Check final learn plan** for formatted candidates:
   ```bash
   cat .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/learn-plan.md
   ```
   Verify tripwire candidates have copy-paste ready YAML

4. **Manual validation**: Compare detected candidates against manually-identified tripwire-worthy items from the session

## Test Cases

| Session Contains | Expected |
|-----------------|----------|
| Error requiring `--no-interactive` | Detected as candidate (cross-cutting + silent failure) |
| TypeError in single function | NOT a candidate (not cross-cutting) |
| Silent data corruption bug | Candidate (destructive + silent failure) |
| API rate limit hit | Candidate if affects multiple commands |