<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2026-02-19T18:37:43.647049+00:00'
created_by: schrockn
plan_comment_id: null
last_dispatched_run_id: '22204813274'
last_dispatched_node_id: WFR_kwLOPxC3hc8AAAAFK4KP2g
last_dispatched_at: '2026-02-19T23:39:52.090731+00:00'
last_local_impl_at: null
last_local_impl_event: null
last_local_impl_session: null
last_local_impl_user: null
last_remote_impl_at: null
last_remote_impl_run_id: null
last_remote_impl_session_id: null
branch_name: plan-plan-skip-impl-for-draft-p-02-19-1837
created_from_session: c2b88dd1-9acd-4f67-ab21-981e1a87a084

```

</details>
<!-- /erk:metadata-block:plan-header -->

---

<details>
<summary><code>original-plan</code></summary>

# Plan: Skip .impl/ for Draft PR Backend, Use impl-context Instead

## Context

When the draft PR backend (`ERK_PLAN_BACKEND=draft_pr`) is active, plans live in `.erk/impl-context/plan.md` (committed to the plan branch at plan-save time) rather than being stored as GitHub issues. The current code always creates a `.impl/` folder during implementation setup, even for draft PR plans — duplicating content already on the branch and creating confusion. Additionally, `erk exec impl-init` can't find the plan in `.erk/impl-context/`, breaking the `plan-implement` flow.

Two changes are needed:
1. Don't create `.impl/` when the draft PR backend is active
2. Make `impl-init` recognize `.erk/impl-context/` as a valid plan location

## Files to Modify

- `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py`
- `src/erk/cli/commands/implement.py`
- `src/erk/cli/commands/exec/scripts/impl_init.py`
- `tests/unit/cli/commands/exec/scripts/test_impl_init.py`
- `.gitignore`

## Key Infrastructure to Reuse

- `IMPL_CONTEXT_DIR = ".erk/impl-context"` — `erk_shared.plan_store.draft_pr_lifecycle:86`
- `save_plan_ref(impl_dir, *, provider, plan_id, url, labels, objective_id)` — `erk_shared.impl_folder:125`
- `read_plan_ref(impl_dir) -> PlanRef | None` — `erk_shared.impl_folder:167` (reads `plan-ref.json` first)
- Draft PR detection: `isinstance(plan_branch, str) and plan_branch` (already on line 111 of `setup_impl_from_issue.py`)
- Draft PR backend name: `ctx.plan_store.get_provider_name() == "github-draft-pr"`

## Implementation Steps

### Step 1: `setup_impl_from_issue.py` — Skip `.impl/`, write plan-ref to impl-context

In the "Step 3" block (lines 178–200), split on `is_draft_pr_plan`. For draft PR plans, save `plan-ref.json` into `.erk/impl-context/` (which already exists on the checked-out branch) instead of creating `.impl/`:

```python
# Step 3: Create .impl/ folder or save plan reference
impl_path_str: str | None = None

if not no_impl:
    is_draft_pr_plan = isinstance(plan_branch, str) and plan_branch
    if is_draft_pr_plan:
        impl_context_dir = cwd / IMPL_CONTEXT_DIR
        impl_path_str = str(impl_context_dir)
        save_plan_ref(
            impl_context_dir,
            provider="github-draft-pr",
            plan_id=str(issue_number),
            url=plan.url,
            labels=(),
            objective_id=plan.objective_id,
        )
    else:
        impl_path = cwd / ".impl"
        impl_path_str = str(impl_path)
        create_impl_folder(worktree_path=cwd, plan_content=plan.body, overwrite=True)
        save_plan_ref(
            impl_path,
            provider="github",
            plan_id=str(issue_number),
            url=plan.url,
            labels=(),
            objective_id=plan.objective_id,
        )
```

Add `from erk_shared.plan_store.draft_pr_lifecycle import IMPL_CONTEXT_DIR` to imports.

Note: `is_draft_pr_plan` is evaluated here (not reusing the earlier variable at line 111) to keep the block self-contained.

### Step 2: `implement.py` (`_implement_from_issue`) — Skip `.impl/` for draft PR backend

Detect draft PR backend via `ctx.plan_store.get_provider_name()` and skip `.impl/` creation. Instead, write `plan-ref.json` to `.erk/impl-context/`:

```python
provider_name = ctx.plan_store.get_provider_name()

if provider_name == "github-draft-pr":
    from erk_shared.plan_store.draft_pr_lifecycle import IMPL_CONTEXT_DIR
    impl_context_dir = ctx.cwd / IMPL_CONTEXT_DIR
    if not impl_context_dir.exists():
        user_output(
            click.style("Error: ", fg="red")
            + f"Expected {IMPL_CONTEXT_DIR}/ directory not found. "
            "Ensure you are on the plan branch."
        )
        raise SystemExit(1)
    save_plan_ref(
        impl_context_dir,
        provider=provider_name,
        plan_id=str(issue_number),
        url=plan.url,
        labels=(),
        objective_id=plan.objective_id,
    )
else:
    ctx.console.info("Creating .impl/ folder with plan...")
    create_impl_folder(worktree_path=ctx.cwd, plan_content=plan.body, overwrite=True)
    ctx.console.success("✓ Created .impl/ folder")
    impl_dir = ctx.cwd / ".impl"
    save_plan_ref(
        impl_dir,
        provider=provider_name,
        plan_id=str(issue_number),
        url=plan.url,
        labels=(),
        objective_id=plan.objective_id,
    )
    ctx.console.success(f"✓ Saved plan reference: {plan.url}")
```

### Step 3: `impl_init.py` — Add `.erk/impl-context/` as third fallback

Update `_validate_impl_folder()` to check `.erk/impl-context/` after `.worker-impl/`:

```python
from erk_shared.plan_store.draft_pr_lifecycle import IMPL_CONTEXT_DIR

def _validate_impl_folder() -> tuple[Path, str]:
    cwd = Path.cwd()

    impl_dir = cwd / ".impl"
    impl_type = "impl"

    if not impl_dir.exists():
        impl_dir = cwd / ".worker-impl"
        impl_type = "worker-impl"

    if not impl_dir.exists():
        impl_dir = cwd / IMPL_CONTEXT_DIR
        impl_type = "impl-context"

    if not impl_dir.exists():
        _error_json(
            "no_impl_folder",
            "No .impl/, .worker-impl/, or .erk/impl-context/ folder found in current directory",
        )

    plan_file = impl_dir / "plan.md"
    if not plan_file.exists():
        _error_json("no_plan_file", f"No plan.md found in {impl_dir}")

    return impl_dir, impl_type
```

When `impl_type == "impl-context"`, `read_plan_ref(impl_dir)` finds `plan-ref.json` written in Step 1, returning a full `PlanRef` with `plan_id` = PR number. This makes `has_issue_tracking = True` and `issue_number = <PR number>` so the `plan-implement` command can call `setup-impl-from-issue <issue_number>` for syncing.

### Step 4: `.gitignore` — Prevent `plan-ref.json` from being committed

`plan-ref.json` is a local ephemeral file created alongside the committed `plan.md` and `ref.json` in `.erk/impl-context/`. Add to `.gitignore`:

```
.erk/impl-context/plan-ref.json
```

### Step 5: `test_impl_init.py` — Tests for impl-context fallback

Add two tests:

1. **`test_impl_init_detects_impl_context`**: Create `.erk/impl-context/plan.md` only (no `.impl/`). Assert `impl_type == "impl-context"`, `valid == True`.

2. **`test_impl_init_impl_context_with_plan_ref`**: Create `.erk/impl-context/plan.md` + `plan-ref.json` (provider=`github-draft-pr`, plan_id=`456`, url=PR URL). Assert `has_issue_tracking == True`, `issue_number == 456`.

Update `test_impl_init_errors_missing_impl_folder` to expect the new error message that mentions `.erk/impl-context/`.

## Verification

1. Run unit tests: `pytest tests/unit/cli/commands/exec/scripts/test_impl_init.py`
2. Manual test with `ERK_PLAN_BACKEND=draft_pr erk exec setup-impl-from-issue <draft-pr-number>`:
   - Confirm no `.impl/` folder created
   - Confirm `.erk/impl-context/plan-ref.json` exists
3. Run `erk exec impl-init --json` on a draft PR branch:
   - Expect `{"valid": true, "impl_type": "impl-context", "has_issue_tracking": true, "issue_number": <pr_number>}`


</details>
---


To checkout this PR in a fresh worktree and environment locally, run:

```
source "$(erk pr checkout 7638 --script)" && erk pr sync --dangerous
```
