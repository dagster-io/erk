# Plan: Eliminate Mocking from download_remote_session Tests

**Part of Objective #7129, Step 3.2**

## Context

`tests/unit/cli/commands/exec/scripts/test_download_remote_session.py` uses 13 `unittest.mock` calls (`MagicMock`, `patch`) to simulate HTTP responses from `urllib.request.urlopen`. This violates erk's testing convention of dependency injection over mocking. The goal is to make URL fetching injectable so tests use fake fetchers instead of patching.

## Approach: Extract Core Logic + Callable Injection

**Key insight:** The existing `HttpClient` gateway is JSON-API-focused (returns `dict[str, Any]`). These scripts do raw binary downloads. Rather than extending the gateway, we inject a simple `url_fetcher: Callable[[str], bytes]` parameter.

### Files to Modify

1. **`src/erk/cli/commands/exec/scripts/download_remote_session.py`** — Extract logic, add fetcher parameter
2. **`tests/unit/cli/commands/exec/scripts/test_download_remote_session.py`** — Rewrite 4 tests to use fake fetchers

### Phase 1: Refactor Source (`download_remote_session.py`)

1. **Add `url_fetcher` parameter to `_download_from_gist`:**
   ```python
   def _download_from_gist(
       gist_url: str,
       session_dir: Path,
       *,
       url_fetcher: Callable[[str], bytes],
   ) -> Path | str:
       normalized_url = normalize_gist_url(gist_url)
       try:
           content = url_fetcher(normalized_url)
           ...
   ```

2. **Create `_real_url_fetch` production implementation:**
   ```python
   def _real_url_fetch(url: str) -> bytes:
       with urllib.request.urlopen(url) as response:
           return response.read()
   ```

3. **Extract `_execute_download` function** containing all logic from the Click command (directory setup, cleanup, download, result formatting):
   ```python
   def _execute_download(
       *,
       repo_root: Path,
       gist_url: str,
       session_id: str,
       url_fetcher: Callable[[str], bytes],
   ) -> tuple[int, dict[str, object]]:
       """Core download logic. Returns (exit_code, output_dict)."""
   ```

4. **Slim the Click command** to a thin wrapper:
   ```python
   @click.command(name="download-remote-session")
   ...
   def download_remote_session(ctx, gist_url, session_id):
       repo_root = require_repo_root(ctx)
       exit_code, output = _execute_download(
           repo_root=repo_root, gist_url=gist_url, session_id=session_id,
           url_fetcher=_real_url_fetch,
       )
       click.echo(json.dumps(output))
       if exit_code != 0:
           raise SystemExit(exit_code)
   ```

### Phase 2: Rewrite Tests (`test_download_remote_session.py`)

**Tests that stay unchanged** (no mocking needed): tests 1-7 (helper functions, URL normalization, CLI argument validation).

**4 tests to rewrite** — call `_execute_download` directly with fake fetchers instead of patching `urlopen`:

| Current Test | New Approach |
|---|---|
| `test_cli_success_with_gist_download` | Call `_execute_download` with `lambda url: content.encode()` |
| `test_cli_error_gist_download_fails` | Call `_execute_download` with fetcher that raises `URLError` |
| `test_cli_cleanup_existing_directory_on_redownload` | Call `_execute_download` with fake fetcher; verify old files removed |
| `test_cli_success_with_webpage_url_normalized` | Call `_execute_download` with capturing fetcher; verify normalized URL |

**Remove imports:** `MagicMock`, `patch` — replaced by `_execute_download`, `_real_url_fetch` imports.

**Rename tests** to reflect they test core logic, not CLI (e.g., `test_success_download`, `test_error_download_fails`).

## Verification

1. Run tests: `pytest tests/unit/cli/commands/exec/scripts/test_download_remote_session.py`
2. Confirm no `unittest.mock` imports remain in the test file
3. Run type checker: `ty check src/erk/cli/commands/exec/scripts/download_remote_session.py`
4. Run linter: `ruff check` on both files