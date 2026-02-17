# Fix: One-shot dispatch uses .worker-impl/ instead of .impl/

## Context

`dispatch_one_shot()` in `one_shot_dispatch.py` writes the instruction to `.impl/task.md` and tries to `git add` it. This fails because `.impl/` is in `.gitignore`. The `plan submit` flow already solved this correctly by using `.worker-impl/` (not gitignored), which the remote workflow then copies to `.impl/`. The one-shot dispatch should follow the same pattern.

The workflow at `one-shot.yml:96-106` already has a fallback that writes the instruction from the workflow input if `.impl/task.md` doesn't exist on the branch. But that path truncates at 500 chars and uses shell `printf`, which is fragile for long/complex instructions. Committing the full instruction via `.worker-impl/` is the correct approach.

## Changes

### 1. `src/erk/cli/commands/one_shot_dispatch.py` (lines 198-234)

Replace the `.impl/` write+stage with `.worker-impl/`:

```python
# Before (lines 198-206):
impl_dir = repo.root / ".impl"
impl_dir.mkdir(parents=True, exist_ok=True)
task_file = impl_dir / "task.md"
task_file.write_text(params.instruction + "\n", encoding="utf-8")
ctx.git.commit.stage_files(repo.root, [".impl/task.md"])

# After:
worker_impl_dir = repo.root / ".worker-impl"
worker_impl_dir.mkdir(parents=True, exist_ok=True)
task_file = worker_impl_dir / "task.md"
task_file.write_text(params.instruction + "\n", encoding="utf-8")
ctx.git.commit.stage_files(repo.root, [".worker-impl/task.md"])
```

Update the truncation message (line 234):
```
"... (full instruction committed to .impl/task.md)"
→ "... (full instruction committed to .worker-impl/task.md)"
```

### 2. `.github/workflows/one-shot.yml` (lines 96-106)

Update the workflow step to read from `.worker-impl/task.md` instead of `.impl/task.md`:

```yaml
- name: Write instruction to .impl/task.md
  env:
    INSTRUCTION: ${{ inputs.instruction }}
  run: |
    if [ -f .worker-impl/task.md ]; then
      echo "Instruction already committed to .worker-impl/task.md"
      mkdir -p .impl
      cp .worker-impl/task.md .impl/task.md
    else
      mkdir -p .impl
      printf '%s\n' "$INSTRUCTION" > .impl/task.md
      echo "Instruction written to .impl/task.md from workflow input"
    fi
```

The step name can also be updated. The key change: if `.worker-impl/task.md` exists on the branch (committed by the CLI), copy it to `.impl/task.md`. Otherwise fall back to the workflow input (for backwards compat with in-flight runs).

### 3. `tests/commands/one_shot/test_one_shot_dispatch.py`

Update assertions in two tests:

- **`test_dispatch_happy_path()`** (line 59): `(".impl/task.md",)` → `(".worker-impl/task.md",)`, and update file path assertions (lines 62-64)
- **`test_dispatch_long_instruction_truncates_workflow_input()`** (lines 270-277): Update file path from `.impl` to `.worker-impl`, and update the truncation suffix assertion (line 268)

## Verification

1. Run tests: `pytest tests/commands/one_shot/test_one_shot_dispatch.py`
2. Run broader one-shot tests: `pytest tests/commands/one_shot/`
3. Run objective implement tests: `pytest tests/commands/objective/test_implement_one_shot.py`