# Fix: pr-address remote workflow not updating plan metadata

## Context

The `pr-address.yml` GitHub Actions workflow (triggered by `/erk:pr-address-remote` → `erk launch pr-address`) does not update plan-header metadata after execution. This means:
- The TUI's "remote" column stays "-" for pr-address runs (no `last_remote_impl_at`)
- No `last_remote_impl_run_id` is recorded
- No session capture/upload happens

By contrast, `plan-implement.yml` updates `last_remote_impl_at`, `last_remote_impl_run_id`, `last_remote_impl_session_id`, and `branch_name` after every run.

The CLI trigger (`launch_cmd.py:151`) does call `maybe_update_plan_dispatch_metadata()` to set dispatch metadata, but the workflow itself sets nothing.

## Change: Add 4 steps to `.github/workflows/pr-address.yml`

Single file change. All steps follow the existing pattern from `plan-implement.yml:254-297`.

### Step 1: Extract plan ID from branch (after "Checkout PR branch", before "Save pre-implementation HEAD")

```yaml
      - name: Extract plan ID from branch
        id: plan_info
        run: |
          BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)
          echo "branch_name=$BRANCH_NAME" >> $GITHUB_OUTPUT
          # Replicate extract_leading_issue_number regex from erk_shared/naming.py:727
          if [[ "$BRANCH_NAME" =~ ^[Pp]?([0-9]+)- ]]; then
            echo "plan_id=${BASH_REMATCH[1]}" >> $GITHUB_OUTPUT
            echo "Extracted plan ID: ${BASH_REMATCH[1]} from branch: $BRANCH_NAME"
          else
            echo "No plan ID found in branch: $BRANCH_NAME (not a plan branch)"
          fi
```

- Placed right after `gh pr checkout` when branch is available
- For non-plan branches (e.g., `feature-xyz`, `plnd/*`), `plan_id` output is not set → all downstream steps skip

### Step 2: Capture session ID (after "Push changes", before summary comment)

```yaml
      - name: Capture session ID
        id: session
        if: always()
        run: |
          if OUTPUT=$(erk exec capture-session-info --path "$GITHUB_WORKSPACE" 2>/dev/null); then
            eval "$OUTPUT"
            echo "session_id=$SESSION_ID" >> "$GITHUB_OUTPUT"
            echo "session_file=$SESSION_FILE" >> "$GITHUB_OUTPUT"
            echo "Captured session ID: $SESSION_ID"
          else
            echo "No session found for: $GITHUB_WORKSPACE"
          fi
```

### Step 3: Upload session (conditional on both session + plan ID)

```yaml
      - name: Upload session to gist and update plan header
        if: always() && steps.session.outputs.session_id && steps.plan_info.outputs.plan_id
        continue-on-error: true
        env:
          GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }}
          PLAN_ID: ${{ steps.plan_info.outputs.plan_id }}
          SESSION_ID: ${{ steps.session.outputs.session_id }}
          SESSION_FILE: ${{ steps.session.outputs.session_file }}
        run: |
          erk exec upload-session \
            --session-file "$SESSION_FILE" \
            --session-id "$SESSION_ID" \
            --source remote \
            --plan-id "$PLAN_ID"
```

### Step 4: Update plan header with remote impl info (conditional on plan ID)

```yaml
      - name: Update plan header with remote impl info
        if: always() && steps.plan_info.outputs.plan_id
        continue-on-error: true
        env:
          GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }}
          PLAN_ID: ${{ steps.plan_info.outputs.plan_id }}
          RUN_ID: ${{ github.run_id }}
          SESSION_ID: ${{ steps.session.outputs.session_id }}
          BRANCH_NAME: ${{ steps.plan_info.outputs.branch_name }}
        run: |
          TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S+00:00")
          erk exec update-plan-header "$PLAN_ID" \
            "last_remote_impl_at=$TIMESTAMP" \
            "last_remote_impl_run_id=$RUN_ID" \
            "last_remote_impl_session_id=$SESSION_ID" \
            "branch_name=$BRANCH_NAME"
```

## Final step order

1. `actions/checkout@v4` (existing)
2. `erk-remote-setup` (existing)
3. Checkout PR branch (existing)
4. **Extract plan ID from branch** (NEW)
5. Save pre-implementation HEAD (existing)
6. Address PR review comments (existing)
7. Clean up plan staging dirs (existing)
8. Push changes (existing)
9. **Capture session ID** (NEW)
10. **Upload session** (NEW)
11. **Update plan header** (NEW)
12. Generate and post summary comment (existing)

## What does NOT change

- **`launch_cmd.py`**: Already calls `maybe_update_plan_dispatch_metadata()` correctly
- **Schema**: All fields already exist in `PlanHeaderSchema`
- **TUI code**: Already reads `last_remote_impl_at` and displays it
- **Exec commands**: `update-plan-header`, `capture-session-info`, `upload-session` all exist

## Edge cases

- **Non-plan PRs**: `plan_info` emits no `plan_id` → all new steps skip silently
- **Plan without plan-header block**: `update-plan-header` fails → `continue-on-error: true` catches it
- **Claude step fails**: `if: always()` ensures metadata still gets recorded
- **Session not found**: Session upload skips; metadata update still runs with empty session_id
- **`plnd/*` branches (draft PR backend)**: Regex doesn't match → skips (same as `maybe_update_plan_dispatch_metadata`)

## Verification

1. Push the change
2. Find a PR on a P{N}-* branch, trigger `erk launch pr-address --pr <N>`
3. After workflow completes, check the plan issue body for updated `last_remote_impl_at` and `last_remote_impl_run_id`
4. Open `erk dash -i` with runs enabled and verify the "remote" column shows a timestamp
5. Verify the run URL link works from the TUI
