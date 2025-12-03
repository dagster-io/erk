---
title: Kit CLI Commands
read_when:
  - "creating kit CLI commands"
  - "understanding Python/LLM boundary"
  - "implementing kit command patterns"
---

# Kit CLI Commands - Python/LLM Boundary Standards

This guide defines the boundary between Python and LLM responsibilities in kit CLI commands that interact with Claude Code.

## Core Principle

**Python reduces tokens. LLM does semantic inference.**

Kit CLI commands exist to preprocess data and orchestrate workflows. The LLM handles all tasks requiring understanding, judgment, or creativity.

## The Fundamental Distinction

### Preprocessing vs Inference

- **Preprocessing** = Mechanical data reduction that doesn't require understanding
- **Inference** = Understanding content, making judgments, creative composition

| Operation                           | Type          | Owner  |
| ----------------------------------- | ------------- | ------ |
| Filter logs by entry type           | Preprocessing | Python |
| Compress XML by removing whitespace | Preprocessing | Python |
| Extract title from markdown         | Inference     | LLM    |
| Generate descriptive filename       | Inference     | LLM    |
| Parse semantic meaning from logs    | Inference     | LLM    |
| Format text with templates          | Inference     | LLM    |

**Key Question:** "Does this operation require understanding the meaning of the text?"

- **YES** → LLM responsibility
- **NO** → Could be Python (if it reduces tokens)

## Python Responsibilities

Python in kit CLI commands should handle:

### 1. Token Reduction

- Filter unnecessary log entries
- Remove redundant data
- Compress structure (not content)
- Extract relevant sections by position

**Example (CORRECT):**

```python
# Filter session log entries by type
def filter_entries(entries: list[dict]) -> list[dict]:
    """Remove non-essential entries to reduce tokens."""
    return [
        entry for entry in entries
        if entry["type"] in ("tool_use", "tool_result", "assistant", "user")
    ]
```

### 2. Data Structure Operations

- JSON serialization/deserialization
- File I/O (reading, writing)
- Subprocess execution
- Path manipulation (directories, not content)

**Example (CORRECT):**

```python
# Read and parse JSON
def load_discoveries(path: Path) -> dict[str, Any]:
    """Load discoveries from JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Discoveries file not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))
```

### 3. Infrastructure Orchestration

- Multi-phase workflows
- Temporary file management
- Command-line argument parsing
- Exit code handling

**Example (CORRECT):**

```python
# Orchestrate two-phase workflow
def execute_discover(session_id: str, cwd: Path) -> None:
    """Phase 1: Discover and preprocess session logs."""
    # Find project directory
    project_dir = find_project_dir(cwd)

    # Load and filter logs
    log_entries = load_session_log(project_dir, session_id)
    filtered = filter_entries(log_entries)

    # Compress to XML
    compressed = compress_to_xml(filtered)

    # Output for LLM
    result = {
        "compressed_xml": compressed,
        "stats": compute_stats(log_entries, filtered),
    }
    print(json.dumps(result, indent=2))
```

### 4. Validation

- Schema validation
- Type checking
- Range validation
- File existence checks

### 5. Input Parsing

- URL parsing and validation
- Format detection and extraction
- Data transformation between formats
- Pattern matching for structured input

**Example:** See the [Kit CLI Push Down pattern](../developer/agentic-engineering-patterns/kit-cli-push-down.md) for a complete example of moving bash parsing logic to tested Python commands.

## LLM Responsibilities

The LLM handles all operations requiring understanding:

### 1. Semantic Analysis

- Understanding text meaning
- Identifying patterns in content
- Extracting insights from context
- Recognizing relationships

**Example (CORRECT - in command markdown):**

```markdown
Analyze the compressed session logs to identify:

- Failed approaches and WHY they didn't work
- API quirks discovered through experimentation
- Architectural insights from reasoning
```

### 2. Content Generation

- Writing descriptions
- Composing documentation
- Generating summaries
- Creating explanations

### 3. Naming and Labeling

- Generating filenames based on content
- Creating descriptive titles
- Choosing appropriate identifiers

### 4. Formatting and Composition

- Structuring output documents
- Organizing information hierarchically
- Adapting format to content
- Deciding what to emphasize

## Anti-Patterns

### Anti-Pattern #1: Regex in LLM Prompts

**WRONG - Instructing LLM to use regex:**

````markdown
Extract discoveries using regex patterns:

```python
tool_uses = re.findall(r'<tool_use name="([^"]+)"...', xml, re.DOTALL)
tool_results = re.findall(r'<tool_result tool="([^"]+)"...', xml, re.DOTALL)
```
````

````

**Why it's wrong:** Treats LLM as a string parser instead of leveraging semantic understanding.

**CORRECT - Semantic analysis:**
```markdown
Read the compressed XML and identify:
- Tool invocations and their purpose
- Tool results that revealed errors or insights
- Assistant reasoning about approaches
````

---

### Anti-Pattern #2: Python Text Munging

**WRONG - Python generating names:**

```python
def _generate_filename(plan_lines: list[str]) -> str:
    """Generate filename from plan title."""
    title = _extract_title(plan_lines)
    slug = title.lower().replace(" ", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    return f"{slug[:30]}-plan.md"
```

**Why it's wrong:** Mechanical string operations lose semantic meaning. May truncate important words or create ambiguous names.

**CORRECT - LLM inference:**

```markdown
Generate a descriptive filename for this plan:

- Read the plan objectives and scope
- Create concise kebab-case name (max 30 chars)
- Prioritize clarity over mechanical rules
- Examples: "auth-refactor-plan.md", "api-migration.md"
```

---

### Anti-Pattern #3: Python Template Assembly

**WRONG - Hardcoded templates:**

```python
def execute_assemble(plan: str, discoveries: dict) -> str:
    """Assemble enhanced plan with template."""
    output = []
    output.append("# Enhanced Plan\n")
    output.append("## Executive Summary\n")
    output.append(_extract_summary(plan))
    output.append("\n## Discoveries\n")

    for category, items in discoveries["categories"].items():
        output.append(f"### {category}\n")
        for item in items:
            output.append(f"- {item}\n")

    return "".join(output)
```

**Why it's wrong:** Rigid structure doesn't adapt to content. LLM can't optimize organization or emphasis.

**CORRECT - LLM composition:**

```markdown
Compose an enhanced plan from these inputs:

Plan content:
{plan_content}

Discoveries:
{discoveries_json}

Suggested structure (adapt as needed):

- Executive Summary (synthesize from plan goals)
- Critical Context (key discoveries affecting implementation)
- Implementation Plan (from original)
- Session Discoveries (organized by relevance)
- Failed Attempts (what didn't work and why)

Feel free to reorder, combine, or adapt sections for maximum clarity.
```

---

### Anti-Pattern #4: Python Parsing Semantic Content

**WRONG - Parsing structure for meaning:**

```python
def _extract_summary(plan_lines: list[str]) -> str:
    """Extract summary from plan structure."""
    in_summary = False
    summary_lines = []

    for line in plan_lines:
        if line.startswith("## "):
            if in_summary:
                break
            if "summary" in line.lower():
                in_summary = True
        elif in_summary and line.strip():
            summary_lines.append(line)

    return "\n".join(summary_lines) or "No summary available"
```

**Why it's wrong:** Relies on positional structure, not semantic understanding. Breaks if format changes.

**CORRECT - LLM understanding:**

```markdown
Read this plan and extract an executive summary:

- Identify the main objective
- Summarize the approach
- Highlight key decisions
- 2-3 sentences maximum
```

## Architecture Patterns

### Pattern 1: Two-Phase CLI with JSON Protocol

**Structure:**

```
Phase 1 (Python) → JSON → LLM Analysis → JSON → Phase 2 (Python)
```

**Example:**

```python
# Phase 1: Preprocess (reduce tokens)
def execute_discover(session_id: str, cwd: Path) -> None:
    log_entries = load_session_log(session_id)
    filtered = filter_entries(log_entries)  # 85% reduction
    compressed = compress_to_xml(filtered)

    print(json.dumps({
        "compressed_xml": compressed,
        "stats": {...}
    }))

# Phase 2: Accept LLM output (no post-processing)
def execute_assemble(plan_path: Path, discoveries_path: Path) -> None:
    plan = plan_path.read_text(encoding="utf-8")
    discoveries = json.loads(discoveries_path.read_text(encoding="utf-8"))

    # Return for LLM to compose (no templates!)
    print(json.dumps({
        "plan_content": plan,
        "discoveries": discoveries
    }))
```

**LLM's role (in command markdown):**

```markdown
1. Call `dot-agent kit-command erk command discover`
2. Parse JSON output
3. Analyze compressed_xml semantically
4. Structure discoveries as JSON
5. Call `dot-agent kit-command erk command assemble`
6. Compose final output from returned data
```

### Pattern 2: Preprocessing Pipeline

**Correct flow:**

```
Raw Data → Filter → Compress → JSON → LLM Inference
  (Python)   (Python)  (Python)   (Python)   (LLM)
```

**Example:**

```python
def preprocess_session_logs(entries: list[dict]) -> str:
    """Reduce token count while preserving semantic content."""
    # 1. Filter by relevance
    relevant = [e for e in entries if is_relevant(e)]

    # 2. Remove system noise
    cleaned = [remove_system_messages(e) for e in relevant]

    # 3. Compress structure
    compressed = compress_to_xml(cleaned)

    # 4. Return for LLM analysis
    return compressed
```

## Decision Framework

Use this flowchart to decide Python vs LLM:

```
                 ┌─────────────────────────┐
                 │ Need to process data?   │
                 └───────────┬─────────────┘
                             │
                ┌────────────▼────────────┐
                │ Does it reduce tokens?  │
                └────────────┬────────────┘
                      │              │
                    YES             NO
                      │              │
                      ▼              ▼
            ┌─────────────┐    ┌─────────────────────┐
            │ Mechanical?  │    │ Understand content? │
            └──────┬───────┘    └─────────┬───────────┘
                   │                       │
              YES  │  NO              YES  │  NO
                   │                       │
                   ▼                       ▼
            ┌───────────┐          ┌──────────┐
            │  PYTHON   │          │   LLM    │
            │(filtering)│          │(analysis)│
            └───────────┘          └──────────┘
```

**Examples:**

| Task                          | Reduces Tokens? | Mechanical? | Understand? | Owner    |
| ----------------------------- | --------------- | ----------- | ----------- | -------- |
| Filter log entries by type    | YES             | YES         | NO          | Python   |
| Extract title from markdown   | NO              | NO          | YES         | LLM      |
| Remove whitespace from XML    | YES             | YES         | NO          | Python   |
| Generate descriptive filename | NO              | NO          | YES         | LLM      |
| Parse JSON structure          | YES             | YES         | NO          | Python   |
| Identify failed approaches    | NO              | NO          | YES         | LLM      |
| Slugify text (replace spaces) | NO              | YES         | NO          | Neither! |
| Compose document structure    | NO              | NO          | YES         | LLM      |

**Special case - Slugification:** This is mechanical but doesn't reduce tokens AND loses semantic meaning. It's wrong in both Python and LLM. Instead, ask LLM to generate appropriate names directly.

## Case Study: `/erk:save-session-enriched-plan`

### Before Refactoring (Anti-Patterns)

**Problem 1: Regex in command markdown**

````markdown
### Step 3: Mine Discoveries

Extract discoveries using regex patterns:

```python
tool_uses = re.findall(r'<tool_use name="([^"]+)"...', xml, re.DOTALL)
```
````

````

❌ **Anti-pattern:** LLM instructed to parse mechanically instead of understanding semantically

---

**Problem 2: Python slugification**
```python
def _generate_filename(plan_lines: list[str]) -> str:
    title = _extract_title(plan_lines)
    slug = title.lower().replace(" ", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    return f"{slug[:30]}-enhanced-plan.md"
````

❌ **Anti-pattern:** Python doing naming (semantic task) with mechanical operations

---

**Problem 3: Python template assembly**

```python
def execute_assemble(plan_path: Path, discoveries_path: Path) -> None:
    output = ["# Enhanced Plan\n"]
    output.append("## Executive Summary\n")
    output.append(_extract_summary(plan_lines))
    output.append("\n## Discoveries\n")
    # ... more template logic
    return "".join(output)
```

❌ **Anti-pattern:** Rigid template prevents LLM from adapting structure to content

---

**Problem 4: Python parsing content**

```python
def _extract_title(plan_lines: list[str]) -> str:
    for line in plan_lines:
        if line.startswith("# "):
            return line.lstrip("# ").strip()
    return "Implementation Plan"
```

❌ **Anti-pattern:** Python parsing semantic content based on position

### After Refactoring (Correct Patterns)

**Solution 1: Semantic analysis in command markdown**

```markdown
### Step 3: Mine Discoveries Semantically

Read the compressed XML and analyze it to identify:

**Failed Attempts:**

- Approaches that didn't work and WHY
- Errors encountered with their context
- Solutions that were rejected and reasons

**API Quirks:**

- Undocumented behaviors discovered
- Edge cases found through experimentation
- Workarounds that became necessary

[Continue with semantic prompts for other categories...]
```

✅ **Correct:** LLM uses semantic understanding, not regex

---

**Solution 2: LLM generates filename**

```markdown
### Step 5b: Generate Filename

Read the plan content and generate an appropriate filename:

- Consider the plan's objectives and scope
- Create concise kebab-case name (max 30 chars for git worktree)
- Prioritize clarity and descriptiveness
- Examples: "auth-refactor-plan.md", "api-migration.md"
```

✅ **Correct:** LLM generates name based on understanding

---

**Solution 3: LLM composes structure**

```markdown
### Step 5c: Compose Enhanced Plan

Using the plan content and discoveries, compose an enhanced plan:

Suggested sections (adapt based on content):

- Executive Summary (synthesize from objectives)
- Critical Context (discoveries affecting implementation)
- Implementation Plan (from original)
- Session Discoveries (organized by relevance)
- Failed Attempts (what didn't work and why)

Feel free to reorder, combine, or adapt sections for maximum clarity.
```

✅ **Correct:** LLM composes with flexible structure

---

**Solution 4: Python only does infrastructure**

```python
def execute_assemble(plan_path: Path, discoveries_path: Path) -> None:
    """Assemble enhanced plan (LLM composition, not templates)."""

    # Python: Read inputs (infrastructure only)
    plan_content = plan_path.read_text(encoding="utf-8")
    discoveries = json.loads(discoveries_path.read_text(encoding="utf-8"))

    # Python: Return for LLM to compose (no parsing, no templates)
    result = {
        "plan_content": plan_content,
        "discoveries": discoveries,
    }

    print(json.dumps(result, indent=2))
```

✅ **Correct:** Python does pure infrastructure, LLM does all inference

### Impact

**Before:**

- ❌ LLM instructed to use regex (Step 3: ~90 lines)
- ❌ Python has 6 inference functions (~170 lines)
- ❌ Rigid template structure
- ❌ Mechanical naming (truncates at 30 chars)

**After:**

- ✅ LLM does semantic analysis (natural language prompts)
- ✅ Python only infrastructure (~40 lines)
- ✅ Flexible structure adapts to content
- ✅ Contextual naming based on understanding

**Token Economics:**

- Session log preprocessing: 85% token reduction (227K → 32K) ✅ KEPT
- LLM inference quality: Improved (semantic vs regex) ✅ GAINED
- Python maintenance: Reduced (170 → 40 lines) ✅ GAINED

## Summary

**Golden Rules:**

1. **Python preprocesses, LLM infers** - If it reduces tokens mechanically, use Python. If it requires understanding, use LLM.

2. **Never give LLM regex patterns** - LLM should analyze semantically, not parse mechanically.

3. **Never put templates in Python** - LLM should compose structure based on content.

4. **Never slugify in Python** - LLM should generate appropriate names contextually.

5. **Python is infrastructure** - File I/O, JSON, subprocess, validation. Nothing more.

**Decision shortcut:** "Does this require understanding what the text means?" → LLM. Otherwise, consider Python only if it reduces tokens.

## Command Loading and Naming Conventions

Kit CLI commands are loaded lazily by `LazyKitGroup` in `dot_agent_kit/commands/kit_command/group.py`.

### Naming Convention

Command names use **kebab-case**, function names use **snake_case**:

| Command Name (kit.yaml) | Expected Function Name |
| ----------------------- | ---------------------- |
| `get-closing-text`      | `get_closing_text`     |
| `plan-save-to-issue`    | `plan_save_to_issue`   |
| `submit-branch`         | `submit_branch`        |

The loader converts hyphens to underscores automatically (line 133 in `group.py`).

### Handling Import Collisions

When your CLI command function would collide with an imported function name, use an import alias:

**Problem:**

```python
from erk_shared.impl_folder import get_closing_text  # Collision!

@click.command(name="get-closing-text")
def get_closing_text() -> None:  # Same name as import
    closing_text = get_closing_text(impl_dir)  # Which one?
```

**Solution - use import alias:**

```python
from erk_shared.impl_folder import get_closing_text as get_closing_text_impl

@click.command(name="get-closing-text")
def get_closing_text() -> None:
    closing_text = get_closing_text_impl(impl_dir)  # Clear!
```

**DO NOT** rename the function with a `_cmd` suffix - this breaks the loader's name resolution.

### Validation Rules

Commands are validated during loading. Each command must have:

1. **Name**: lowercase letters, numbers, hyphens only (`^[a-z][a-z0-9-]*$`)
2. **Path**: must end with `.py` and start with `kit_cli_commands/`
3. **Description**: non-empty string
4. **No directory traversal**: path cannot contain `..`

### Warning Sources

If you see warnings during kit loading, check:

1. **"does not have expected function"** - Function name doesn't match command name (see naming convention above)
2. **"Command file not found"** - Path in kit.yaml doesn't exist
3. **"Failed to import command"** - Python import error in the command file
4. **"Invalid command"** - Validation error (name format, path, description)
