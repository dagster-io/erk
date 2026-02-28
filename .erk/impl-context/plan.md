# Embed Session XML in Learn Plan PR Diffs

## Context

Learn plan PRs (e.g., #8487) currently commit only `plan.md` and `ref.json` to `.erk/impl-context/`. The preprocessed session XML files that informed the learn plan exist in scratch storage at save time but are not persisted in the PR. Embedding them in the diff makes the source material reviewable alongside the plan in the "Files Changed" tab.

## Approach

Add a `--session-xml-dir` CLI option to `plan-save`. When provided, read all `*.xml` files from the directory and commit them under `.erk/impl-context/sessions/` alongside `plan.md` and `ref.json`. Update the learn skill to pass the directory.

No gateway changes needed -- `commit_files_to_branch` already accepts `dict[str, str]` with arbitrary paths.

## Files to Modify

### 1. `src/erk/cli/commands/exec/scripts/plan_save.py`

**Add CLI option** (after `--summary` at line 491):
```python
@click.option(
    "--session-xml-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Directory containing session XML files to embed in the PR diff",
)
```

**Thread parameter** through all three functions:
- `plan_save()` signature + body → `_save_plan_via_planned_pr()` call
- `_save_plan_via_planned_pr()` signature + body → `_save_as_planned_pr()` call
- `_save_as_planned_pr()` signature

**Build files dict with XML entries** in `_save_as_planned_pr` (replacing the inline dict at line 222-230):
```python
files: dict[str, str] = {
    f"{IMPL_CONTEXT_DIR}/plan.md": plan_content,
    f"{IMPL_CONTEXT_DIR}/ref.json": json.dumps(ref_data, indent=2),
}

if session_xml_dir is not None and session_xml_dir.is_dir():
    for xml_file in sorted(session_xml_dir.glob("*.xml")):
        if xml_file.is_file():
            files[f"{IMPL_CONTEXT_DIR}/sessions/{xml_file.name}"] = xml_file.read_text(encoding="utf-8")

git.commit.commit_files_to_branch(
    repo_root, branch=branch_name, files=files, message=f"Add plan: {title}",
)
```

Key decisions:
- `sorted()` for deterministic commit ordering
- `glob("*.xml")` to exclude `.json` files that also live in the learn directory
- `sessions/` subdirectory to keep impl-context tidy
- LBYL: `is_dir()` + `is_file()` checks

### 2. `.claude/commands/erk/learn.md`

**Update Step 7** (around line 693) -- add `--session-xml-dir` to the plan-save command:
```bash
CMD="erk exec plan-save \
    --plan-type learn \
    --plan-file .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/learn-plan.md \
    --session-id=\"${CLAUDE_SESSION_ID}\" \
    --learned-from-issue <parent-issue-number> \
    --session-xml-dir .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn \
    --format json"
```

The session XML directory `.erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn/` contains the preprocessed files from Step 4.

### 3. `tests/unit/cli/commands/exec/scripts/test_plan_save.py`

Add 3 tests following existing patterns (uses `fake_git.branch_commits[0].files` for assertions):

1. **`test_planned_pr_includes_session_xml_files`** -- create XML dir with 2 files, verify both committed under `sessions/`
2. **`test_planned_pr_session_xml_dir_only_includes_xml`** -- create dir with `.xml`, `.json`, `.txt` files, verify only `.xml` committed
3. **`test_planned_pr_without_session_xml_dir_backward_compat`** -- verify existing behavior unchanged when option not passed (only 2 files committed)

## Verification

1. Run `pytest tests/unit/cli/commands/exec/scripts/test_plan_save.py` to verify tests pass
2. Run `ty` and `ruff` for type/lint checks
3. Manually test with `/erk:learn` on a real plan to confirm XML files appear in PR diff
