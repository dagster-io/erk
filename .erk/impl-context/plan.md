# Documentation Plan: Replace gist transport with branch-based materials for learn pipeline

## Context

PR #7733 replaced the gist-based transport mechanism in erk's learn pipeline with a branch-based approach. Previously, the learn pipeline packed preprocessed materials (session analyses, diff analysis, gap analysis) into a single GitHub gist using a delimiter-based format, then the CI workflow downloaded and unpacked them. The new approach commits materials directly to a `learn/{plan_id}` branch in `.erk/impl-context/`, which CI checks out to access the files without any download or parsing step. This eliminated two exec scripts (`upload_learn_materials.py`, `download_learn_materials.py`), their tests, and the associated gist API calls.

This documentation plan matters because multiple existing docs actively describe the old gist-based flow as current behavior. Agents consulting these docs will encounter phantom references to deleted files, obsolete function names, and incorrect pipeline descriptions. The stale documentation is not merely incomplete — it is actively misleading. Additionally, the implementation surfaced several non-obvious patterns (force-push for re-learn idempotency, the distinction between learn gists and session gists, `.erk/impl-context/` leakage risk on PR branches) that agents will encounter again without documented guidance.

The implementation spanned three sessions and a PR review cycle. Key challenges included: inventing a nonexistent `delete_remote_branch` gateway method (resolved by force-push), forgetting the required `force` kwarg on `create_branch`, accidentally committing `.erk/impl-context/` files to the PR branch, and needing to regenerate exec reference docs after deleting exec scripts. Each of these produced a tripwire candidate.

## Raw Materials

Branch: `learn/7733` (PR #7733)

## Summary

| Metric                          | Count |
| ------------------------------- | ----- |
| Documentation items             | 14    |
| Contradictions to resolve       | 7     |
| Tripwire candidates (score>=4)  | 5     |
| Potential tripwires (score 2-3) | 3     |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action. These must be resolved before creating new content.

### 1. Archive gist-materials-interchange.md

**Location:** `docs/learned/architecture/gist-materials-interchange.md`
**Action:** DELETE_STALE
**Phantom References:** `upload_learn_materials.py` (MISSING), `download_learn_materials.py` (MISSING)
**Cleanup Instructions:** This document describes the delimiter-based gist packing/unpacking format that was entirely removed in PR #7733. Both primary source files it references are deleted. Add a superseded header pointing to the replacement doc (`learn-branch-transport.md`), or delete the file outright. Do not attempt to update in place — the core concept no longer exists.

### 2. Remove stale gist-format tripwire from planning/tripwires.md

**Location:** `docs/learned/planning/tripwires.md`
**Action:** DELETE_STALE_ENTRY
**Phantom References:** Tripwire bullet referencing `download-learn-materials` gist format parser
**Cleanup Instructions:** Remove the tripwire bullet that references `download-learn-materials` or `upload-learn-materials`. Both exec scripts are deleted. Verify no other tripwires in this file reference these deleted commands.

## Documentation Items

### HIGH Priority

#### 1. Update learn-pipeline-workflow.md (Stages 4-5 rewrite)

**Location:** `docs/learned/planning/learn-pipeline-workflow.md`
**Action:** UPDATE
**Source:** [Impl] [PR #7733]

**Draft Content:**

```markdown
<!-- Rewrite Stages 4 and 5 of the pipeline. Remove all references to
     upload_learn_materials.py, download_learn_materials.py, and
     combine_learn_material_files(). Replace with: -->

## Stage 4: Branch Creation

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py -->

The trigger_async_learn script creates a `learn/{plan_id}` branch from `origin/master`,
copies preprocessed materials into `.erk/impl-context/`, commits them, and force-pushes
the branch to origin. This replaces the former gist upload step.

Key behaviors:

- Branch naming convention: `learn/{plan_id}` (e.g., `learn/7733`)
- Uses `git.branch.*` and `git.remote.*` gateways directly (NOT BranchManager)
- try/finally pattern ensures the original branch is always restored after commit
- Re-learn idempotency: uses `force=True` on `push_to_remote` to overwrite existing remote branch
- Stats reporting uses bytes (not chars)

## Stage 5: Workflow Trigger

The script triggers `learn.yml` via `workflow_dispatch` with the `learn_branch` input
(not `gist_url`). CI checks out the branch via `ref: ${{ inputs.learn_branch }}`,
making `.erk/impl-context/` files immediately available without any download step.

After the learn run completes, CI auto-cleans the branch:
`git push origin --delete ${{ inputs.learn_branch }} || true`

<!-- Also update: pipeline diagram, failure modes table, debugging section.
     Remove all phantom refs to upload_learn_materials.py /
     download_learn_materials.py / combine_learn_material_files(). -->
```

#### 2. Update async-learn-local-preprocessing.md

**Location:** `docs/learned/planning/async-learn-local-preprocessing.md`
**Action:** UPDATE
**Source:** [Impl] [PR #7733]

**Draft Content:**

```markdown
<!-- Rewrite the "Material Assembly Pipeline" section. The old description
     ("All files are packed into a single gist using the delimiter-based format")
     is completely replaced. New content: -->

## Material Assembly Pipeline

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py -->

After preprocessing completes, materials are committed to a `learn/{plan_id}` branch
in the `.erk/impl-context/` directory. The branch is force-pushed to origin, and the
`learn.yml` workflow is triggered with the branch name as input.

This replaces the former gist-based transport (removed in PR #7733). The branch-based
approach eliminates delimiter parsing, avoids gist API rate limits, and gives CI direct
file access via checkout.

<!-- Also update:
     - Workflow trigger description: gist_url input -> learn_branch input
     - Stats metric: chars -> bytes
     - --skip-workflow flag: now commits to learn branch instead of uploading gist
     - Remove gist-referencing tripwires from this doc
     - Add tripwire: "Do NOT use BranchManager for learn branches — use git.branch.* directly"
     - TriggerSuccess output field: gist_url -> learn_branch -->
```

#### 3. Update learn-command-conditional-pipeline.md

**Location:** `docs/learned/cli/learn-command-conditional-pipeline.md`
**Action:** UPDATE
**Source:** [Impl] [PR #7733]

**Draft Content:**

```markdown
<!-- Replace all references to the old function and field names:
     - _get_learn_materials_gist_url() -> _get_learn_materials_branch()
     - learn_materials_gist_url field -> learn_materials_branch field
     - Return value is now a branch name (e.g., "learn/7733"), not a URL
     - LearnPreprocessResult.gist_url -> LearnPreprocessResult.learn_branch -->

## Conditional Pipeline Entry Point

<!-- Source: src/erk/cli/commands/learn/learn_cmd.py -->

The learn command checks plan metadata for a `learn_materials_branch` field. If present,
the plan has preprocessed materials on a branch (set during `erk land`). The function
`_get_learn_materials_branch()` reads this field and returns the branch name, or None
if learn has not been triggered for this plan.

<!-- The conditional pattern (check metadata -> invoke /erk:learn -> fall through to
     interactive) remains valid. Only the transport mechanism and field names changed. -->
```

#### 4. Create learn-branch-transport.md

**Location:** `docs/learned/architecture/learn-branch-transport.md`
**Action:** CREATE
**Source:** [Impl] [PR #7733]

**Draft Content:**

```markdown
---
title: Learn Branch Transport
read_when:
  - modifying the learn pipeline's material delivery mechanism
  - working with learn/{plan_id} branches
  - debugging learn.yml CI failures related to missing materials
  - implementing re-learn or learn retry workflows
tripwires:
  - action: "creating or pushing a learn/* branch"
    warning: "Use git.branch.* and git.remote.* directly — NOT BranchManager. Learn branches are not Graphite-tracked. See learn-branch-transport.md."
  - action: "pushing a learn branch that may already exist on remote"
    warning: "Use force=True on push_to_remote. Do NOT call delete_remote_branch — this method does not exist on GitRemoteOps ABC."
---

# Learn Branch Transport

The learn pipeline delivers preprocessed materials to CI via temporary git branches,
replacing the former gist-based transport (removed in PR #7733).

## Why Branches Over Gists

- Eliminates delimiter-based packing/unpacking (source of parsing bugs)
- Avoids GitHub Gist API rate limits
- CI gets direct file access via `ref:` checkout — no download step

## Branch Naming and Lifecycle

Convention: `learn/{plan_id}` (e.g., `learn/7733`).

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py -->

Lifecycle:

1. `trigger_async_learn` creates branch from `origin/master`
2. Copies preprocessed files to `.erk/impl-context/` on that branch
3. Commits and force-pushes to origin
4. Triggers `learn.yml` with `learn_branch` input
5. CI checks out the branch, reads `.erk/impl-context/` files directly
6. After completion, CI deletes the branch: `git push origin --delete`

## Critical Constraints

- **NOT BranchManager**: Learn branches use `git.branch.*` directly. They are not
  Graphite-tracked and must not go through BranchManager.
- **try/finally for branch restoration**: After creating and committing to the learn
  branch, always restore the original branch in a `finally` block. This is resource
  cleanup (not EAFP exception-based control flow) and is the approved pattern.
- **Re-learn idempotency**: Use `force=True` on `push_to_remote` to overwrite an
  existing remote branch. Do NOT attempt `delete_remote_branch` — that method does
  not exist on the GitRemoteOps ABC.
- **force kwarg on create_branch**: The `force: bool` parameter is required.
  Always pass it explicitly (`force=False` for first-time, `force=True` for re-create).

## Related Documentation

- [impl-context.md](../planning/impl-context.md) — `.erk/impl-context/` directory lifecycle
- [learn-pipeline-workflow.md](../planning/learn-pipeline-workflow.md) — Full pipeline stages
- [async-learn-local-preprocessing.md](../planning/async-learn-local-preprocessing.md) — Preprocessing step details
```

#### 5. Remove stale gist-format tripwire

**Location:** `docs/learned/planning/tripwires.md`
**Action:** DELETE_STALE_ENTRY
**Source:** [Impl] [PR #7733]

**Draft Content:**

```markdown
<!-- Remove the tripwire bullet that references download-learn-materials
     gist format parser. Both upload_learn_materials.py and
     download_learn_materials.py are deleted. The tripwire is now invalid.

     Scan the entire file for any other references to:
     - download-learn-materials
     - upload-learn-materials
     - gist_url (in learn pipeline context — session gists are separate)
     Remove all such stale entries. -->
```

#### 6. Update learn-workflow.md

**Location:** `docs/learned/planning/learn-workflow.md`
**Action:** UPDATE
**Source:** [Impl] [PR #7733]

**Draft Content:**

```markdown
<!-- Updates needed:
     1. Remove gist_url from PlanSynthesizer inputs table
     2. Update CI flow description: CI checks out learn/{plan_id} branch,
        .erk/impl-context/ files are present immediately after checkout
     3. Remove /erk:learn gist_url= parameter reference — command is now
        just /erk:learn {plan_id} with no transport parameter
     4. Update "no PR context" flow: references branch creation step
        instead of gist upload
     5. Note that Claude auto-detects .erk/impl-context/ existence
        after CI checkout — no parameter needed -->
```

#### 7. Update learn-without-pr-context.md

**Location:** `docs/learned/planning/learn-without-pr-context.md`
**Action:** UPDATE
**Source:** [Impl] [PR #7733]

**Draft Content:**

```markdown
<!-- Replace "skips straight to gist upload" with "skips straight to
     branch creation step". The graceful degradation path now creates
     the learn/{plan_id} branch with available materials (omitting
     diff analysis) instead of uploading to a gist.

     Verify no other gist references remain in this doc. -->
```

### MEDIUM Priority

#### 8. Update impl-context.md (learn branch lifecycle)

**Location:** `docs/learned/planning/impl-context.md`
**Action:** UPDATE
**Source:** [Impl] [PR #7733]

**Draft Content:**

```markdown
<!-- Add a new section documenting the learn pipeline's use of .erk/impl-context/.
     The existing content about draft-PR plan saving remains valid. -->

## Learn Pipeline Use

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py -->

The learn pipeline uses `.erk/impl-context/` as a staging area on `learn/{plan_id}`
branches. During `trigger_async_learn`, preprocessed materials (session analyses, diff
analysis, gap analysis) are copied into `.erk/impl-context/` on a temporary branch,
committed, and pushed to origin. CI checks out this branch and reads the files directly.

Lifecycle on learn branches:

1. Created by `trigger_async_learn` during the branch commit step
2. Contains preprocessed learn materials (not plan/ref files)
3. Read by CI after checking out the learn branch
4. Auto-deleted when CI cleans up the branch after the learn run

**Leakage risk**: `.erk/impl-context/` files on learn branches are intentional learn
materials. Do NOT apply the normal "leaked impl-context" cleanup procedure to
`learn/*` branches. The cleanup procedure applies only to `plan/*` branches where
these files should never be committed.

Pre-commit sanity check: on `plan/*` branches, run `git ls-files .erk/impl-context/`
before committing — the result must be empty.
```

#### 9. Create gist-systems.md (dual-system disambiguation)

**Location:** `docs/learned/architecture/gist-systems.md`
**Action:** CREATE
**Source:** [Impl] [PR #7733]

**Draft Content:**

```markdown
---
title: Gist Systems in Erk
read_when:
  - scoping gist-related cleanup or refactoring
  - confused about which gist system is active vs removed
  - working with download_remote_session.py or get_learn_sessions.py
tripwires:
  - action: "removing or modifying gist-related code"
    warning: "Erk has two independent gist systems. The learn materials gist was removed in PR #7733. The session upload/download gist is still active. See gist-systems.md to confirm which system you are touching."
---

# Gist Systems in Erk

Erk historically had two independent systems that used GitHub gists. Agents must
distinguish between them when scoping cleanup or modification work.

## 1. Learn Materials Gist Transport (REMOVED)

Removed in PR #7733. Formerly used delimiter-based packing to upload preprocessed
learn materials to a gist, which CI then downloaded and unpacked. Replaced by
branch-based transport. See [learn-branch-transport.md](learn-branch-transport.md).

Files deleted: `upload_learn_materials.py`, `download_learn_materials.py`

## 2. Session Upload/Download Gist (STILL ACTIVE)

<!-- Source: src/erk/cli/commands/exec/scripts/download_remote_session.py -->

Used for remote implementation workflows. Session logs are uploaded to gists
for cross-machine access. Key files: `download_remote_session.py`,
`get_learn_sessions.py`. This system is completely independent of the learn
pipeline and remains active.

## Why This Matters

During the PR #7733 implementation, agents confused these two systems when
scoping cleanup work. "Remove all gist code" would incorrectly include the
session system. Always enumerate both systems before making gist-related changes.
```

#### 10. Add try/finally clarification for git cleanup

**Location:** `docs/learned/architecture/tripwires.md` (or appropriate architecture doc)
**Action:** UPDATE
**Source:** [PR #7733]

**Draft Content:**

```markdown
<!-- Add clarification about try/finally vs EAFP -->

## try/finally for Resource Cleanup

The "no exception-based control flow" rule (LBYL, not EAFP) prohibits using try/except
for branching logic. However, try/finally for guaranteed resource cleanup is the
correct and approved pattern. This distinction matters for git operations where a
branch checkout must be restored regardless of success or failure.

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py -->

The canonical example is `trigger_async_learn.py`, which uses try/finally to restore
the original branch after committing to a learn branch. The PR #7733 review bot
explicitly approved this pattern as distinct from EAFP.

Rule of thumb: try/finally (cleanup) = correct. try/except (control flow) = violation.
```

#### 11. Update testing tripwires: source deletion requires test deletion

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7733]

**Draft Content:**

```markdown
<!-- Add a new tripwire entry -->

- action: "deleting a source module"
  warning: "The corresponding test module must also be deleted. Orphaned test files
  that import nonexistent source modules are a CI violation — symmetric to the untested
  source rule. PR #7733 demonstrated this: both upload_learn_materials.py and
  download_learn_materials.py required test deletion alongside source deletion."
```

#### 12. Update learn-plan-metadata-fields.md

**Location:** `docs/learned/planning/learn-plan-metadata-fields.md`
**Action:** UPDATE
**Source:** [Impl] [PR #7733]

**Draft Content:**

```markdown
<!-- Update the plan header fields listing:
     - learn_materials_gist_url -> learn_materials_branch
     - The field now stores a branch name (e.g., "learn/7733") rather than a URL
     - Set during `erk land` by _store_learn_materials_branch()
     - Read during `erk learn` by _get_learn_materials_branch() -->
```

### LOW Priority

#### 13. Update async-learn-local-preprocessing.md (stats metric change)

**Location:** `docs/learned/planning/async-learn-local-preprocessing.md`
**Action:** UPDATE
**Source:** [Impl] [PR #7733]

**Draft Content:**

```markdown
<!-- Minor update: the stats output for materials now reports bytes
     (f"{total_size:,} bytes") instead of chars (f"{total_size:,} chars").
     This is a detectable change in the stderr output format.
     Update any references to the stats output format. -->
```

#### 14. SHOULD_BE_CODE: Add docstring to \_store_learn_materials_branch()

**Location:** `src/erk/cli/commands/land_cmd.py`
**Action:** CODE_CHANGE
**Source:** [Impl] [PR #7733]

The `_store_learn_materials_branch()` function in `land_cmd.py` replaces the former `_store_learn_materials_gist_url()`. It stores the learn branch name (e.g., `learn/7733`) on the plan header metadata so that `erk learn` can later retrieve it. If the function lacks a docstring explaining this lifecycle role, add one describing: what it stores, where it stores it (plan header), and when it runs (during `erk land` after successful learn preprocessing).

## Contradiction Resolutions

### 1. learn-command-conditional-pipeline.md: phantom function name

**Existing doc:** `docs/learned/cli/learn-command-conditional-pipeline.md`
**Conflict:** Doc references `_get_learn_materials_gist_url()` which no longer exists; the function is now `_get_learn_materials_branch()`.
**Resolution:** Update the function name, field name (`learn_materials_branch`), and return value description (branch name, not URL). Covered by Documentation Item #3.

### 2. gist-materials-interchange.md: entire doc is stale

**Existing doc:** `docs/learned/architecture/gist-materials-interchange.md`
**Conflict:** All primary source files described in this doc (`upload_learn_materials.py`, `download_learn_materials.py`) are deleted. The delimiter packing format no longer exists.
**Resolution:** Archive with superseded header or delete entirely. The replacement pattern is documented in the new `learn-branch-transport.md`. Covered by Stale Cleanup Item #1.

### 3. learn-pipeline-workflow.md Stages 4-5: phantom pipeline steps

**Existing doc:** `docs/learned/planning/learn-pipeline-workflow.md`
**Conflict:** Stage 4 ("Gist Upload") references `upload_learn_materials.py`; Stage 5 references downloading from gist. Both files are deleted.
**Resolution:** Rewrite Stages 4-5 to describe branch creation and CI checkout. Covered by Documentation Item #1.

### 4. learn-workflow.md: phantom gist_url input

**Existing doc:** `docs/learned/planning/learn-workflow.md`
**Conflict:** PlanSynthesizer inputs table lists `gist_url` as an input. This parameter was removed; learn.yml now receives `learn_branch`.
**Resolution:** Remove `gist_url` from inputs table; update CI flow description. Covered by Documentation Item #6.

### 5. learn-without-pr-context.md: phantom gist upload path

**Existing doc:** `docs/learned/planning/learn-without-pr-context.md`
**Conflict:** Doc says the no-PR-context path "skips straight to gist upload." This is now branch creation.
**Resolution:** Replace with "skips straight to branch creation step." Covered by Documentation Item #7.

### 6. async-learn-local-preprocessing.md: phantom gist pipeline

**Existing doc:** `docs/learned/planning/async-learn-local-preprocessing.md`
**Conflict:** "Material Assembly Pipeline" section describes gist-based packing as current behavior. The `gist_url` input to learn.yml does not exist.
**Resolution:** Rewrite to describe branch-based transport. Covered by Documentation Item #2.

### 7. planning/tripwires.md: phantom tripwire

**Existing doc:** `docs/learned/planning/tripwires.md`
**Conflict:** Contains a tripwire bullet referencing `download-learn-materials` gist format parser. Both the script and the format are deleted.
**Resolution:** Remove the stale tripwire bullet. Covered by Stale Cleanup Item #2.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Inventing nonexistent gateway methods

**What happened:** The agent called `git.remote.delete_remote_branch()` to clean up an existing remote branch before re-pushing. This method does not exist on the `GitRemoteOps` ABC.
**Root cause:** The agent assumed the method existed without checking the ABC definition. Gateway ABCs are the contract — methods not declared in the ABC do not exist.
**Prevention:** Before any `git.*.*()` call, grep `packages/erk-shared/src/erk_shared/gateway/git/` for the method name. The ABC is the ground truth.
**Recommendation:** TRIPWIRE (score 6 — see Tripwire Candidates #2)

### 2. Missing required keyword argument on create_branch

**What happened:** Called `git.branch.create_branch(repo_root, learn_branch, "origin/master")` without the required `force: bool` keyword argument. ty raised `missing-argument`.
**Root cause:** The `force` parameter is required (no default value), but this is not obvious from the method name alone.
**Prevention:** Check the ABC signature before calling. Always include `force=False` or `force=True` explicitly.
**Recommendation:** TRIPWIRE (score 4 — see Tripwire Candidates #5)

### 3. .erk/impl-context/ files leaked into PR commit

**What happened:** During implementation, the `.erk/impl-context/` staging directory files (`plan.md`, `ref.json`) were accidentally committed to the PR branch. A tripwire bot caught this during review.
**Root cause:** The branch-based transport creates real files in `.erk/impl-context/`. Without explicit exclusion, `git add` operations can include them.
**Prevention:** On `plan/*` branches, run `git ls-files .erk/impl-context/` before committing — result must be empty. Use `git rm -rf .erk/impl-context/` if files are staged.
**Recommendation:** TRIPWIRE (score 8 — see Tripwire Candidates #1)

### 4. Exec reference docs not regenerated after script deletion

**What happened:** After deleting `upload_learn_materials.py` and `download_learn_materials.py`, CI failed the Exec Reference Check because `.claude/skills/erk-exec/reference.md` was out of sync.
**Root cause:** `erk-dev gen-exec-reference-docs` must be run after any exec script addition, modification, or deletion. This is a non-obvious CI requirement.
**Prevention:** Run `erk-dev gen-exec-reference-docs` as part of any exec script change workflow.
**Recommendation:** TRIPWIRE (score 6 — see Tripwire Candidates #3)

### 5. Test assertions referencing old field names after rename

**What happened:** After renaming `TriggerSuccess.gist_url` to `TriggerSuccess.learn_branch`, test assertions in `test_trigger_async_learn.py` still used `output["gist_url"]`, causing `KeyError`.
**Root cause:** When renaming output fields on exec commands, the test files under `tests/unit/cli/commands/exec/scripts/` were not in the initial grep for files to update.
**Prevention:** When renaming fields in exec script dataclasses, always grep `tests/unit/cli/commands/exec/scripts/` separately for the old field name.
**Recommendation:** ADD_TO_DOC (testing docs — not cross-cutting enough for a tripwire)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. .erk/impl-context/ leakage into PR commits

**Score:** 8/10 (criteria: Non-obvious +2, Destructive potential +2, Silent failure +2, Repeated pattern +1, Cross-cutting +1)
**Trigger:** Before committing on a `plan/*` branch
**Warning:** "Run `git ls-files .erk/impl-context/` — result must be empty. The `.erk/impl-context/` directory is a temporary staging area and must never be committed to a PR branch. Use `git rm -rf .erk/impl-context/` if staged."
**Target doc:** `docs/learned/planning/tripwires.md`

This is the highest-scoring tripwire candidate because the failure is silent (CI does not catch it — only the tripwire bot review does), the damage is visible to reviewers, and it actually happened during this implementation. The `.erk/impl-context/` directory serves two purposes (plan-saving staging and learn-branch materials) on different branch types, making the leakage risk non-obvious. On `learn/*` branches the files are intentional; on `plan/*` branches they must never be committed.

### 2. Check git gateway ABC before calling any method

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +1, External tool quirk +1)
**Trigger:** Before calling any `git.remote.*`, `git.branch.*`, or `git.commit.*` method
**Warning:** "Grep `packages/erk-shared/src/erk_shared/gateway/git/` for the method name first. The ABC is the contract — methods do not exist unless declared in the ABC. Do not invent method names."
**Target doc:** `docs/learned/architecture/tripwires.md`

This tripwire addresses the pattern of agents assuming gateway methods exist. During this implementation, the agent invented `delete_remote_branch` — a plausible-sounding method that simply does not exist. ty catches this, but only after the code is written. Checking the ABC first saves a write-diagnose-rewrite cycle.

### 3. Exec reference doc regeneration after exec script changes

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** After adding, modifying, or deleting files under `src/erk/cli/commands/exec/scripts/`
**Warning:** "Run `erk-dev gen-exec-reference-docs` to regenerate `.claude/skills/erk-exec/reference.md`. CI runs an Exec Reference Check that will fail if this step is skipped."
**Target doc:** `docs/learned/planning/tripwires.md` or `docs/learned/cli/tripwires.md`

This is non-obvious because the reference doc is in `.claude/skills/`, not in `docs/`, and the CI check name does not hint at what needs to be regenerated. Every exec script change — including deletion — triggers this requirement.

### 4. force=True on push_to_remote for re-learn (NOT delete_remote_branch)

**Score:** 5/10 (criteria: Non-obvious +2, Destructive potential +2, External tool quirk +1)
**Trigger:** When pushing a learn branch that may already exist on remote
**Warning:** "Use `force=True` on `push_to_remote`. Do NOT call `delete_remote_branch` — this method does not exist on the GitRemoteOps ABC."
**Target doc:** `docs/learned/architecture/tripwires.md`

This combines two insights: the correct approach (force-push) and the incorrect one (delete-then-push). The force-push pattern is idempotent and handles both first-time and re-learn scenarios. Placing this in architecture tripwires ensures any agent working with remote branch operations sees it.

### 5. create_branch requires explicit force kwarg

**Score:** 4/10 (criteria: Non-obvious +2, Silent failure +2)
**Trigger:** When calling `git.branch.create_branch(...)`
**Warning:** "Always include `force=False` or `force=True` as an explicit keyword argument — the `force: bool` parameter is required and ty will raise `missing-argument` if omitted."
**Target doc:** `docs/learned/architecture/tripwires.md`

This is a narrow tripwire but earned its score because the failure is delayed (ty diagnostic, not a runtime error) and the parameter name does not suggest it would be required rather than optional. Agents working with branch creation will encounter this.

## Potential Tripwires

Items with score 2-3 that may warrant promotion with additional context:

### 1. .erk/impl-context/plan.md prettier compliance

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** This is specific to the branch-based transport workflow — only applies when `plan.md` is written during the learn branch commit step. Prettier CI checks are well-known in the project generally, but the fact that `.erk/impl-context/plan.md` is subject to them is not obvious because the directory feels like a transient staging area. Promote to full tripwire if this recurs in future learn pipeline modifications.

### 2. Learn materials gist vs session gist scope confusion

**Score:** 3/10 (criteria: Non-obvious +2, Cross-cutting +1)
**Notes:** The risk of confusing these two systems decreases significantly once `gist-systems.md` is created (Documentation Item #9). If agents still conflate the systems after the doc exists, promote to a tripwire. Recommend creating the doc first and observing.

### 3. Ruff E501 in test docstrings

**Score:** 1/10
**Notes:** Pure style concern. Does not meet tripwire threshold. Include as a footnote in testing docs if pattern recurs, but not worth a tripwire entry.
