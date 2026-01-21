# Plan: Unified Gist-Based Session Storage (Step 2.6)

**Part of Objective #4991, Step 2.6**

## Summary

Unify local and remote session storage to both use GitHub Gists, replacing the current artifact-based approach for remote sessions.

**Key constraint:** GitHub Actions artifacts can ONLY be uploaded from within a workflow context - no REST API or CLI exists for external upload. Rather than having two different storage mechanisms, we unify on gists.

**Solution:** Use GitHub Gists (secret/unlisted) for ALL session storage:
- Can be created via `gh gist create` from any context (local CLI or CI)
- Secret by default (URL-accessible but not discoverable)
- No time-based retention limits (artifacts expire after 30-90 days)
- Single codepath for both local and remote sessions

## Implementation

### Phase 1: GitHub Gateway Extension

**File:** `packages/erk-shared/src/erk_shared/github/abc.py`

Add method to GitHub ABC:
```python
@abstractmethod
def create_gist(
    self,
    *,
    filename: str,
    content: str,
    description: str,
    public: bool,
) -> GistCreated | GistCreateError:
```

Return types (new dataclasses):
```python
@dataclass(frozen=True)
class GistCreated:
    gist_id: str
    gist_url: str
    raw_url: str  # Direct URL to file content

@dataclass(frozen=True)
class GistCreateError:
    message: str
```

Implement in all 5 gateway files:
- `abc.py` - abstract method
- `real.py` - via `gh gist create --filename X --public=false`
- `fake.py` - in-memory tracking with `created_gists` list
- `dry_run.py` - print-only, return fake GistCreated
- `printing.py` - delegate to wrapped

### Phase 2: Schema Extension

**File:** `packages/erk-shared/src/erk_shared/github/metadata/schemas.py`

Add new constants (replacing run_id-based fields):
```python
LAST_SESSION_GIST_URL: Literal["last_session_gist_url"] = "last_session_gist_url"
LAST_SESSION_GIST_ID: Literal["last_session_gist_id"] = "last_session_gist_id"
LAST_SESSION_ID: Literal["last_session_id"] = "last_session_id"
LAST_SESSION_AT: Literal["last_session_at"] = "last_session_at"
LAST_SESSION_SOURCE: Literal["last_session_source"] = "last_session_source"  # "local" or "remote"
```

Update `PlanHeaderSchema.validate()` and `optional_fields`.

**Note:** Keep existing `last_remote_impl_*` fields for backward compatibility with existing issues.

### Phase 3: Plan Header Update Function

**File:** `packages/erk-shared/src/erk_shared/github/metadata/plan_header.py`

Add unified function:
```python
def update_plan_header_session_gist(
    *,
    issue_body: str,
    gist_url: str,
    gist_id: str,
    session_id: str,
    session_at: str,
    source: Literal["local", "remote"],
) -> str:
```

Updates all session gist fields atomically.

### Phase 4: Upload Session Command

**File:** `src/erk/cli/commands/exec/scripts/upload_session.py`

Create new exec command:
- `--plan-issue` (required): GitHub issue number
- `--session-id` (required): Claude session ID to upload
- `--source` (optional): "local" or "remote", defaults to "local"

**Behavior:**
1. Find session file via `ClaudeInstallation.find_session_globally(session_id)`
2. Read session content
3. Create secret gist via `github.create_gist()`
4. Update plan issue metadata via `update_plan_header_session_gist()`

**Output:** JSON with success, gist_url, gist_id, session_id

### Phase 5: Download Session Command Update

**File:** `src/erk/cli/commands/exec/scripts/download_remote_session.py`

Update to support gist-based download:
- Add `--gist-url` option as alternative to `--run-id`
- When gist URL provided: use `gh gist view <id> --raw`
- Store in same location: `.erk/scratch/remote-sessions/{session_id}/session.jsonl`

Or create new command `download-gist-session` and have both available.

### Phase 6: CI Workflow Update

**File:** `.github/workflows/erk-impl.yml`

Replace artifact upload with gist upload:

```yaml
# Before (artifact-based)
- name: Upload session artifact
  uses: actions/upload-artifact@v4
  with:
    name: session-${{ steps.session.outputs.session_id }}
    path: ${{ steps.session.outputs.session_file }}

# After (gist-based)
- name: Upload session to gist
  if: always() && steps.session.outputs.session_id
  env:
    GH_TOKEN: ${{ github.token }}
  run: |
    erk exec upload-session \
      --plan-issue "${{ inputs.issue_number }}" \
      --session-id "${{ steps.session.outputs.session_id }}" \
      --source remote
```

Remove the `actions/upload-artifact` step and `update-plan-remote-session` step (replaced by upload-session).

### Phase 7: Session Discovery Integration

**File:** `src/erk/cli/commands/exec/scripts/get_learn_sessions.py`

Update to:
1. Parse `last_session_gist_url` from plan-header metadata
2. Return unified `session_sources` with `source_type: "gist"`
3. Maintain backward compatibility: also check `last_remote_impl_run_id` for old issues

### Phase 8: Registration

**File:** `src/erk/cli/commands/exec/group.py`

Register `upload_session` command.

## Files to Modify

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/github/abc.py` | Add `create_gist()` method + result types |
| `packages/erk-shared/src/erk_shared/github/real.py` | Implement `create_gist()` via gh CLI |
| `tests/fakes/github/fake_github.py` | Add `create_gist()` fake with tracking |
| `packages/erk-shared/src/erk_shared/github/dry_run.py` | Add `create_gist()` dry-run |
| `packages/erk-shared/src/erk_shared/github/printing.py` | Add `create_gist()` delegation |
| `packages/erk-shared/src/erk_shared/github/metadata/schemas.py` | Add gist-based session fields |
| `packages/erk-shared/src/erk_shared/github/metadata/plan_header.py` | Add `update_plan_header_session_gist()` |
| `src/erk/cli/commands/exec/scripts/upload_session.py` | **NEW** - Unified upload command |
| `tests/unit/cli/commands/exec/scripts/test_upload_session.py` | **NEW** - Unit tests |
| `src/erk/cli/commands/exec/scripts/download_remote_session.py` | Add `--gist-url` option |
| `src/erk/cli/commands/exec/scripts/get_learn_sessions.py` | Parse gist metadata, maintain backward compat |
| `.github/workflows/erk-impl.yml` | Replace artifact upload with gist upload |
| `src/erk/cli/commands/exec/group.py` | Register new command |
| `.claude/skills/erk-exec-reference/SKILL.md` | Auto-regenerated |

## Testing

### Unit Tests (test_upload_session.py)
- Test successful gist creation with FakeGitHub and FakeClaudeInstallation
- Test plan-header metadata update after upload
- Test `--source local` vs `--source remote` flag
- Test error: session not found
- Test error: gist creation failure
- Test error: plan issue not found

### Unit Tests for gateway (tests/unit/github/)
- Test `create_gist()` in FakeGitHub tracks state correctly
- Test `create_gist()` returns proper GistCreated structure

### Integration Tests (tests/integration/)
- Test `create_gist()` in RealGitHub actually creates gist (cleanup after)

### Manual Verification
```bash
# 1. Create a test plan issue
# 2. Run upload-session with a test session
erk exec upload-session --plan-issue 123 --session-id test-session-id

# 3. Verify gist was created
gh gist list | grep "Session for plan #123"

# 4. Verify plan-header was updated
erk exec get-plan-metadata 123 last_session_gist_url

# 5. Test download from gist
erk exec download-remote-session --gist-url <gist-url> --session-id test-session-id
```

## Verification

### Local Upload Test
1. Create a local session (run any Claude command)
2. Run `erk exec upload-session --plan-issue <issue> --session-id <session>`
3. Verify JSON output shows success and gist_url
4. Verify `erk exec get-learn-sessions <issue>` returns the gist-based session source

### CI Workflow Test
1. Submit a plan to the remote implementation queue
2. Verify CI workflow uploads session to gist (not artifact)
3. Verify plan-header has `last_session_gist_url` set
4. Verify `erk exec download-remote-session --gist-url <url>` retrieves the session

### Learn Workflow Test
1. Run `/erk:learn <issue>` on an issue with gist-based session
2. Verify it downloads from gist and processes correctly

### Backward Compatibility Test
1. Find an existing issue with `last_remote_impl_run_id` (old artifact-based)
2. Verify `get-learn-sessions` still returns it as downloadable

## Scope Note

The original step 2.6 description was:
> Add `erk exec upload-session-artifact` to upload local session as workflow artifact

This plan **expands the scope** to unify ALL session storage (local AND remote) on GitHub Gists:
- Command name: `upload-session` (works for both local and remote)
- Storage: GitHub Gists for everything (not artifacts)
- CI workflow updated to use gists instead of `actions/upload-artifact`

**Rationale:** GitHub Actions artifacts cannot be uploaded from outside a workflow context. Rather than having two different storage mechanisms (artifacts for remote, gists for local), we unify on gists everywhere. This simplifies the codebase and provides consistent session retrieval.

**Trade-off acknowledged:** Gists are "secret" (URL-accessible but not discoverable) rather than truly repo-private like artifacts. This was discussed and accepted for the benefit of unified codepaths.

## Related Documentation

- Skills to load: `fake-driven-testing`, `dignified-python`
- Reference: `docs/learned/sessions/layout.md` for session file locations
- Reference: `docs/learned/testing/exec-script-testing.md` for test patterns
- Reference: `docs/learned/architecture/gateway-abc-implementation.md` for gateway tripwires