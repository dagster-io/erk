# Fix: Escape pipe characters in objective roadmap table cells

## Context

Node descriptions containing `|` (e.g., `SubmitStackResult | SubmitStackError`) break markdown table rendering because the pipe is interpreted as a column separator. This caused corrupted table rows in objective #9324.

## Files to modify

1. **`packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py:627`** — `render_roadmap_tables()`
2. **`src/erk/cli/commands/exec/scripts/objective_render_roadmap.py:155`** — `_render_roadmap()`

## Approach

Add a shared `escape_md_table_cell(value)` function that sanitizes any string for safe inclusion in a markdown table cell. Apply it uniformly to **all** cell values at both rendering sites — not just descriptions.

The function lives in `erk_shared` since both rendering sites can import from there. Place it alongside the roadmap rendering code in the roadmap module itself (it's the only consumer pattern).

### What to escape

- `|` → `\|` (column separator — the bug that triggered this)
- `\n` → ` ` (newlines would break the row)

## TDD Steps

### Red: Write failing tests first

**Test 1** — `packages/erk-shared/tests/unit/github/metadata/test_roadmap.py`:

New standalone test for the utility:

```python
def test_escape_md_table_cell_pipes() -> None:
    assert escape_md_table_cell("A | B") == r"A \| B"

def test_escape_md_table_cell_newlines() -> None:
    assert escape_md_table_cell("line1\nline2") == "line1 line2"

def test_escape_md_table_cell_no_change() -> None:
    assert escape_md_table_cell("plain text") == "plain text"
```

Add to `TestRenderRoadmapTables`:

```python
def test_pipe_in_description_escaped(self) -> None:
    phases = [
        RoadmapPhase(
            number=1, suffix="", name="Test",
            nodes=[
                RoadmapNode(
                    id="1.1",
                    description="SuccessType | ErrorType",
                    status="pending", plan=None, pr=None,
                    depends_on=None, slug=None,
                ),
            ],
        )
    ]
    result = render_roadmap_tables(phases)
    assert r"SuccessType \| ErrorType" in result
    for line in result.strip().splitlines():
        if line.startswith("|") and "---" not in line:
            assert line.count("|") == 5  # 4 columns = 5 pipe delimiters
```

**Test 2** — `tests/unit/cli/commands/exec/scripts/test_objective_render_roadmap.py`:

```python
def test_render_roadmap_escapes_pipe_in_description() -> None:
    """Pipe characters in descriptions are escaped to avoid breaking markdown tables."""
    phases: list[dict[str, object]] = [
        {
            "name": "Test",
            "steps": [
                {"id": "1.1", "description": "SuccessType | ErrorType"},
            ],
        },
    ]
    result = _render_roadmap(phases)
    assert r"SuccessType \| ErrorType" in result
    for line in result.strip().splitlines():
        if line.startswith("|") and "---" not in line and "Node" not in line:
            assert line.count("|") == 5
```

### Green: Minimal fixes

**1. Add utility in `roadmap.py`** (near top, before `render_roadmap_tables`):

```python
def escape_md_table_cell(value: str) -> str:
    """Escape a string for safe inclusion in a markdown table cell."""
    return value.replace("|", r"\|").replace("\n", " ")
```

Export it from the module (add to imports in test file).

**2. `roadmap.py` `render_roadmap_tables()`** — apply to all cells (lines 625-636):

```python
cells = [
    escape_md_table_cell(step.id),
    escape_md_table_cell(step.description),
]
if any_has_depends_on:
    cells.append(escape_md_table_cell(_format_depends_on(step.depends_on)))
cells.extend(
    [
        escape_md_table_cell(status_display),
        escape_md_table_cell(step.pr if step.pr is not None else "-"),
    ]
)
```

**3. `objective_render_roadmap.py`** — apply to display values only, keep raw for `RoadmapNode`:

```python
step_desc = step_data["description"]
# ... slug logic uses raw step_desc ...

# Escape for table display only
esc = escape_md_table_cell
if any_has_depends_on:
    depends_display = ", ".join(depends_on) if depends_on else "-"
    sections.append(
        f"| {esc(step_id)} | {esc(step_desc)} | {esc(depends_display)} | {esc(status)} | {esc(pr_display)} |"
    )
else:
    sections.append(f"| {esc(step_id)} | {esc(step_desc)} | {esc(status)} | {esc(pr_display)} |")
```

Import: `from erk_shared.gateway.github.metadata.roadmap import escape_md_table_cell`

Raw `step_desc` continues to be used for `RoadmapNode(description=step_desc, ...)` (line 183) — metadata stores unescaped values.

## Verification

1. Run: `uv run pytest packages/erk-shared/tests/unit/github/metadata/test_roadmap.py::TestRenderRoadmapTables::test_pipe_in_description_escaped -xvs`
2. Run: `uv run pytest tests/unit/cli/commands/exec/scripts/test_objective_render_roadmap.py::test_render_roadmap_escapes_pipe_in_description -xvs`
3. Run full test suites for both files to ensure no regressions
