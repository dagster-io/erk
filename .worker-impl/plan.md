# Documentation Extraction Plan

## Objective

Capture learnings and patterns from 4 sessions working on raw extraction plans, GitHub issue storage, and session analysis infrastructure.

## Source Information

**Sessions Analyzed:**
- `3cadd2ec-8622-467e-84b6-f0c5455c44f3` (454KB) - Planning session for metadata blocks
- `9da22b1c-c7fd-4a5b-8372-14b21566f74d` (276KB) - Implementation of raw extraction command
- `b32694bd-c390-47ac-9949-0a87bac1af09` (120KB) - GitHub limits research
- `a373c86b-2fc9-4587-82fe-df46e1fe6f11` (164KB) - Merge conflict resolution

---

## Documentation Items

### Item 1: Fake Constructor Extension Pattern (Category A)

**Type:** Learning Gap  
**Location:** `docs/agent/testing/fake-constructor-extension.md` OR update `fake-driven-testing` skill  
**Action:** Create new doc or extend existing skill  
**Priority:** Medium (recurring pattern, moderate impact)

**Context:**

Session a373c86b showed merge conflict resolution where new Shell ABC methods required corresponding FakeShell implementation. The pattern for extending fake constructors had to be reasoned through from scratch.

**Draft Content:**

```markdown
# Extending Fake Constructors

When adding methods to an ABC that require fake behavior configuration:

## Pattern

1. **Add constructor parameters** for controlling behavior:
   - `_<feature>_raises: bool = False` - Control exception behavior
   - `_<feature>_return_value: T | None = None` - Control return values

2. **Add tracking lists** for test assertions:
   - `_<feature>_calls: list[tuple[...]] = []` - Track invocations

3. **Initialize in `__init__`**:
   ```python
   def __init__(
       self,
       *,
       # ...existing params...
       feature_raises: bool = False,
       feature_return_value: str | None = None,
   ):
       # ...existing initialization...
       self._feature_calls: list[tuple[Path]] = []
       self._feature_raises = feature_raises
       self._feature_return_value = feature_return_value
   ```

4. **Expose via properties** for test assertions:
   ```python
   @property
   def feature_calls(self) -> list[tuple[Path]]:
       return self._feature_calls.copy()
   ```

## Example: FakeShell.run_claude_extraction_plan

From commit c1be84a02:

```python
def __init__(
    self,
    *,
    # ...
    claude_extraction_raises: bool = False,
    extraction_plan_url: str | None = None,
):
    self._extraction_calls: list[tuple[Path]] = []
    self._claude_extraction_raises = claude_extraction_raises
    self._extraction_plan_url = extraction_plan_url

def run_claude_extraction_plan(self, cwd: Path) -> str | None:
    self._extraction_calls.append((cwd,))
    if self._claude_extraction_raises:
        raise subprocess.CalledProcessError(...)
    return self._extraction_plan_url
```
```

---

### Item 2: Metadata Block Code Fence Patterns (Category A)

**Type:** Learning Gap  
**Location:** `docs/agent/github/markdown-escaping.md`  
**Action:** Create new doc in new `docs/agent/github/` section  
**Priority:** High (prevents bugs, quick to document)

**Context:**

Session 3cadd2ec discovered that XML tags like `<session>`, `<user>`, `<assistant>` in GitHub issue comments are interpreted as HTML and disappear. Required debugging and research to discover solution.

**Draft Content:**

```markdown
# GitHub Markdown Escaping

## Problem: XML/HTML Tags Disappear

GitHub interprets tags like `<session>`, `<user>`, `<assistant>` as HTML elements. If the tag isn't recognized HTML, it renders invisibly.

## Solution: Code Fences

Always wrap XML or code-like content in triple-backtick code fences with language tags:

````markdown
```xml
<session>
  <user>message</user>
  <assistant>response</assistant>
</session>
```
````

## When to Use

- Session XML preprocessed output
- Any content with angle brackets `< >`
- Code snippets with HTML/XML-like syntax
- Metadata blocks containing structured data

## Related

- GitHub Issue Limits: [docs/agent/github/issue-limits.md](issue-limits.md)
- Session Content Metadata Blocks: Plan #2332
```

---

### Item 3: Multi-Agent Session Mining Guide (Category A)

**Type:** Learning Gap  
**Location:** `docs/agent/sessions/subagent-mining.md`  
**Action:** Create new doc  
**Priority:** Medium (improves extraction quality)

**Context:**

The `/erk:create-extraction-plan` command emphasizes mining subagent outputs but provides no concrete examples of HOW to do this effectively. Need practical guidance.

**Draft Content:**

```markdown
# Mining Subagent Outputs for Documentation Gaps

When analyzing sessions for extraction plans, subagents (Explore, Plan) often contain the most valuable discoveries.

## Finding Subagent Invocations

Look for `<tool_use name="Task">` blocks in session logs:

```xml
<tool_use name="Task" id="toolu_...">
  <param name="description">Explore metadata block system</param>
  <param name="subagent_type">Explore</param>
  <param name="prompt">Explore how metadata blocks work...</param>
</tool_use>
```

## Reading Agent Output

Each Task returns detailed output. Look for:

**Explore agents:**
- Files discovered and their purposes  
- Patterns found in codebase
- Architectural decisions inferred
- Connections between components

**Plan agents:**
- Approaches considered
- Why alternatives were rejected
- Design decisions and tradeoffs
- Constraints discovered

## Example: Mining for Documentation Gaps

**Raw Agent Output:**
> "The existing provider pattern in data/provider.py uses ABC with abstract methods.
> This follows erk's fake-driven testing pattern where FakeProvider implements the same interface."

**What This Tells Us:**
- **Confirms** ABC pattern is already documented (not a gap)
- **Confirms** fake-driven-testing skill connection exists
- **May indicate gap** if the agent had to discover this (wasn't obvious from routing)

## Anti-Patterns

**Don't just summarize:** ❌ "Agent explored the codebase"  
**Extract insights:** ✅ "Agent discovered metadata blocks use YAML frontmatter with strict schema validation"

**Don't treat as black box:** ❌ "Agent figured it out"  
**Mine the reasoning:** ✅ "Agent compared approaches: inline vs external config, chose inline for atomicity"

## Related

- Session Context Mining: [docs/agent/sessions/context-analysis.md](context-analysis.md)
- Extraction Plan Creation: `.claude/commands/erk/create-extraction-plan.md`
```

---

### Item 4: Raw Extraction Plan Command (Category B)

**Type:** Teaching Gap  
**Location:** Update `docs/agent/index.md` routing + create `docs/agent/commands/raw-extraction-plan.md`  
**Action:** Add to command reference  
**Priority:** High (new feature, needs routing)

**Context:**

Session 9da22b1c implemented `/erk:create-raw-extraction-plan` command but it's not documented in agent docs structure. Need to explain when to use vs the analyzed version.

**Draft Content:**

```markdown
# Raw Extraction Plan Command

## Purpose

`/erk:create-raw-extraction-plan` captures preprocessed session data in a GitHub issue WITHOUT analysis. Used by `erk pr land --extract` for raw context storage.

## When to Use

**Use raw extraction when:**
- Landing PRs with `--extract` flag (automated)
- Want to defer analysis to later
- Building context corpus for training/research

**Use analyzed extraction when:**
- Actively identifying documentation gaps
- Want specific recommendations with draft content
- Doing post-session retrospective

## Command: `/erk:create-raw-extraction-plan`

Auto-selects sessions using same logic as `/erk:create-extraction-plan`:
- If on trunk: current session only
- If current session trivial (<1KB): auto-select substantial sessions
- No user prompts (fully automated)

## Output

Creates GitHub issue with `erk-extraction` label containing:
- Raw preprocessed XML from session(s)
- Wrapped in code fences for GitHub rendering
- Truncated if exceeds 65KB limit

## Related

- Analyzed Extraction: `.claude/commands/erk/create-extraction-plan.md`
- GitHub Issue Limits: `docs/agent/github/issue-limits.md`
- Session Preprocessing: `packages/dot-agent-kit/.../preprocess_session.py`
```

**Routing Update for `docs/agent/index.md`:**

Add under "Commands" section:
```markdown
- **Raw Extraction Plans** → [docs/agent/commands/raw-extraction-plan.md](commands/raw-extraction-plan.md)
  - Read when: Working with `erk pr land --extract` or raw session storage
```

---

### Item 5: GitHub Issue Storage Limits (Category B)

**Type:** Teaching Gap  
**Location:** `docs/agent/github/issue-limits.md`  
**Action:** Create new doc in new `docs/agent/github/` section  
**Priority:** Medium (factual reference, informs design)

**Context:**

Session b32694bd researched GitHub's comment limits. Findings: 65KB per comment, no documented limit on comment count. Relevant for extraction plan storage strategy.

**Draft Content:**

```markdown
# GitHub Issue Storage Limits

## Comment Size Limit

**Maximum:** 65,536 characters per comment

**Implications:**
- Truncate content to ~65,000 chars (leave buffer)
- Add truncation notice if content exceeds limit
- Consider multi-comment chunking for large content

## Comment Count Limit

**Maximum:** No documented limit

**Observed:**
- GitHub supports thousands of comments per issue
- API paginates at 30-100 comments per page
- Performance may degrade on very long threads

## Workarounds for Large Content

1. **Multi-comment chunking:** Post n comments with "Part 1/3" headers
2. **External storage:** Link to gists or raw files
3. **Compression:** Use session preprocessing to reduce size

## Code Example

```python
MAX_COMMENT_SIZE = 65_000  # Leave buffer

if len(content) > MAX_COMMENT_SIZE:
    truncated = content[:MAX_COMMENT_SIZE]
    truncated += "\n\n[TRUNCATED - original size: {} chars]".format(len(content))
    content = truncated
```

## Related

- Metadata Block Rendering: [docs/agent/github/markdown-escaping.md](markdown-escaping.md)
- Multi-Comment Chunking: Plan #2332
```

---

### Item 6: Session Auto-Selection Logic (Category B)

**Type:** Teaching Gap  
**Location:** `docs/agent/sessions/auto-selection.md`  
**Action:** Create new doc  
**Priority:** Medium (design pattern, aids understanding)

**Context:**

Complex session selection logic appears in both `/erk:create-extraction-plan` and `/erk:create-raw-extraction-plan`. Centralize the decision tree.

**Draft Content:**

```markdown
# Session Auto-Selection Logic

Commands that analyze sessions use consistent auto-selection logic to avoid prompting users in automated workflows.

## Decision Tree

```
Is on trunk (main/master)?
├─ YES: Use current session only
└─ NO: Check current session size
    ├─ Current session is substantial (≥1KB)
    │   └─ Use current session
    └─ Current session is trivial (<1KB)
        ├─ Exactly 1 substantial session exists
        │   └─ Auto-select that session
        └─ 2+ substantial sessions exist
            ├─ Automated command (raw extraction)
            │   └─ Auto-select ALL substantial sessions
            └─ Interactive command (analyzed extraction)
                └─ Prompt user to choose
```

## Rationale

**Why auto-select on trunk:**
- Trunk sessions are typically interactive development
- Current session has full context

**Why detect trivial sessions:**
- Common pattern: User launches fresh session just to run extraction command
- Trivial session has no useful content to extract
- Previous sessions contain the actual work

**Why automated commands skip prompts:**
- Used by `erk pr land --extract` in scripted workflows
- Must complete without user interaction
- Safe default: analyze all substantial work from branch

## Implementation

Use `dot-agent run erk list-sessions --min-size 1024`:

```python
result = run("dot-agent run erk list-sessions --min-size 1024")
data = json.loads(result)

if data["branch_context"]["is_on_trunk"]:
    # Use current session
    session_ids = [data["current_session_id"]]
elif data["current_session_id"] not in [s["session_id"] for s in data["sessions"]]:
    # Current session is trivial (filtered out)
    if len(data["sessions"]) == 1:
        session_ids = [data["sessions"][0]["session_id"]]
    else:
        # Multiple substantial sessions
        session_ids = [s["session_id"] for s in data["sessions"]]  # or prompt
```

## Related

- List Sessions Command: `packages/dot-agent-kit/.../list_sessions.py`
- Session Size Filtering: [docs/agent/sessions/size-filtering.md](size-filtering.md)
```

---

## Implementation Order

1. **Item 2** (Code Fence Patterns) - High priority, prevents bugs
2. **Item 4** (Raw Extraction Command) - High priority, new feature docs
3. **Item 5** (GitHub Limits) - Medium priority, factual reference
4. **Item 1** (Fake Constructor Pattern) - Medium priority, recurring pattern
5. **Item 6** (Auto-Selection Logic) - Medium priority, design docs
6. **Item 3** (Subagent Mining) - Medium priority, quality improvement

---

## Related Documentation

**Create new section:** `docs/agent/github/`  
**Update routing:** `docs/agent/index.md`

**Skills to load:**
- None required (documentation task)