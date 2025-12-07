# Extraction Module API Reference

Complete reference for the `erk_shared.extraction` module - programmatic access to session
discovery, selection, preprocessing, and extraction.

## Module Overview

The extraction module provides a two-stage pipeline for converting Claude Code session logs
into usable documentation material:

```
discover_sessions()
    ↓ [min_size filter, newest-first sort]
auto_select_sessions()
    ↓ [branch context determines behavior]
collect_session_context()
    ↓ [orchestrates all steps]
preprocess_session()
    ↓ [Stage 1: mechanical reduction]
(distill_with_haiku() if enabled)
    ↓ [Stage 2: optional semantic filtering]
render_session_content_blocks()
    ↓ [chunk if needed for GitHub]
create_raw_extraction_plan()
    ↓ [create GitHub issue + comments]
```

---

## Data Types

### SessionInfo

```python
from erk_shared.extraction.types import SessionInfo

@dataclass(frozen=True)
class SessionInfo:
    session_id: str      # UUID identifying the session
    path: Path           # Path to JSONL file
    size_bytes: int      # File size
    mtime_unix: float    # Modification timestamp
    is_current: bool     # True if matches current session ID
```

### BranchContext

```python
from erk_shared.extraction.types import BranchContext

@dataclass(frozen=True)
class BranchContext:
    current_branch: str   # Current git branch name
    trunk_branch: str     # Trunk branch (main/master)
    is_on_trunk: bool     # True if current_branch == trunk_branch
```

### SessionContextResult

```python
from erk_shared.extraction.session_context import SessionContextResult

@dataclass
class SessionContextResult:
    combined_xml: str              # Preprocessed session content as XML
    session_ids: list[str]         # Session IDs that were processed
    branch_context: BranchContext  # Git branch context at time of collection
```

### RawExtractionResult

```python
from erk_shared.extraction.types import RawExtractionResult

@dataclass(frozen=True)
class RawExtractionResult:
    success: bool
    issue_url: str | None
    issue_number: int | None
    chunks: int                    # Number of comment chunks created
    sessions_processed: list[str]  # Session IDs included
    error: str | None = None
```

---

## Session Discovery

### get_current_session_id

```python
from erk_shared.extraction.session_discovery import get_current_session_id

def get_current_session_id() -> str | None:
    """Extract current session ID from SESSION_CONTEXT environment variable.

    Returns:
        Session ID string or None if not found.
    """
```

### get_branch_context

```python
from erk_shared.extraction.session_discovery import get_branch_context

def get_branch_context(git: Git, cwd: Path) -> BranchContext:
    """Get git branch context for session selection.

    Args:
        git: Git interface (from ErkContext)
        cwd: Current working directory

    Returns:
        BranchContext with current_branch, trunk_branch, is_on_trunk
    """
```

### discover_sessions

```python
from erk_shared.extraction.session_discovery import discover_sessions

def discover_sessions(
    project_dir: Path,
    current_session_id: str | None,
    min_size: int = 0,
    limit: int = 10
) -> list[SessionInfo]:
    """Discover sessions in Claude Code project directory.

    Args:
        project_dir: Path to ~/.claude/projects/<encoded-path>/
        current_session_id: ID to mark as is_current
        min_size: Minimum file size in bytes
        limit: Maximum sessions to return

    Returns:
        List of SessionInfo sorted by mtime (newest first).
        Agent logs (agent-*.jsonl) are excluded.
    """
```

### encode_path_to_project_folder

```python
from erk_shared.extraction.session_discovery import encode_path_to_project_folder

def encode_path_to_project_folder(path: Path) -> str:
    """Encode filesystem path to Claude Code project folder name.

    Encoding rules:
    1. Prepend with '-'
    2. Replace '/' with '-'
    3. Replace '.' with '-'

    Example:
        /Users/foo/code/myapp → -Users-foo-code-myapp
    """
```

### find_project_dir

```python
from erk_shared.extraction.session_discovery import find_project_dir

def find_project_dir(cwd: Path) -> Path | None:
    """Find Claude Code project directory for a filesystem path.

    Args:
        cwd: Working directory to encode

    Returns:
        Path to ~/.claude/projects/<encoded-path>/ or None if doesn't exist.
    """
```

---

## Session Selection

### auto_select_sessions

```python
from erk_shared.extraction.session_selection import auto_select_sessions

DEFAULT_MIN_SUBSTANTIAL_SIZE = 1024  # bytes

def auto_select_sessions(
    sessions: list[SessionInfo],
    branch_context: BranchContext,
    current_session_id: str | None,
    min_substantial_size: int = DEFAULT_MIN_SUBSTANTIAL_SIZE
) -> list[SessionInfo]:
    """Auto-select sessions based on branch context.

    Selection rules:
    - On trunk: Use current session only
    - Current trivial + substantial exist: Auto-select substantial sessions
    - Current substantial: Use it alone
    - No substantial sessions: Return current (even if trivial)

    Args:
        sessions: Available sessions from discover_sessions()
        branch_context: From get_branch_context()
        current_session_id: Current session to prioritize
        min_substantial_size: Threshold for "substantial" (default: 1024 bytes)

    Returns:
        Selected sessions for preprocessing.
    """
```

---

## Session Preprocessing (Stage 1)

Stage 1 is deterministic mechanical reduction - no semantic judgment.

### preprocess_session

```python
from erk_shared.extraction.session_preprocessing import preprocess_session

def preprocess_session(
    session_path: Path,
    session_id: str | None = None,
    include_agents: bool = True
) -> str:
    """Preprocess session log to compressed XML.

    Stage 1 mechanical reduction:
    - Drops file-history-snapshot entries
    - Strips usage metadata
    - Removes empty text blocks
    - Compacts whitespace (3+ newlines → 1)
    - Deduplicates assistant messages with tool_use

    Args:
        session_path: Path to JSONL session file
        session_id: Filter entries by session ID (optional)
        include_agents: Include agent-*.jsonl files from same directory

    Returns:
        Compressed XML string (NOT semantically filtered).
    """
```

### process_log_file

```python
from erk_shared.extraction.session_preprocessing import process_log_file

def process_log_file(
    log_path: Path,
    session_id: str | None = None
) -> tuple[list[dict], int, int]:
    """Process single JSONL log file with mechanical reduction.

    Args:
        log_path: Path to JSONL file
        session_id: Filter by session ID (optional)

    Returns:
        Tuple of (reduced_entries, total_count, skipped_count)
    """
```

### reduce_session_mechanically

```python
from erk_shared.extraction.session_preprocessing import reduce_session_mechanically

def reduce_session_mechanically(entries: list[dict]) -> list[dict]:
    """Apply Stage 1 deterministic token reduction.

    Operations:
    - Drop file-history-snapshot entries
    - Strip usage metadata from assistant messages
    - Remove empty text blocks
    - Drop sessionId field

    Returns:
        Mechanically reduced entries (no semantic filtering).
    """
```

### generate_compressed_xml

```python
from erk_shared.extraction.session_preprocessing import generate_compressed_xml

def generate_compressed_xml(
    entries: list[dict],
    source_label: str | None = None
) -> str:
    """Convert reduced entries to coarse-grained XML.

    XML structure:
    - <session id="..."> - Container
    - <user> - User messages
    - <assistant> - Assistant responses
    - <tool_use name="..." id="..."> - Tool invocations
    - <tool_result id="..."> - Tool outputs

    Returns:
        XML string representation.
    """
```

---

## Haiku Distillation (Stage 2 - Optional)

Stage 2 applies semantic judgment via Claude Haiku.

### distill_with_haiku

```python
from erk_shared.extraction.llm_distillation import distill_with_haiku

def distill_with_haiku(
    reduced_content: str,
    *,
    session_id: str,
    repo_root: Path | None = None
) -> str:
    """Apply Stage 2 semantic distillation via Haiku.

    Semantic operations:
    - Detect and filter noise (log discovery, warmup content)
    - Deduplicate semantically similar blocks
    - Prune verbose outputs to essential content
    - Preserves errors, stack traces, warnings

    Implementation:
    - Invokes `claude --model haiku` subprocess
    - Piggybacks on Claude Code authentication
    - Writes reduced content to scratch for debugging

    Args:
        reduced_content: Stage 1 output (compressed XML)
        session_id: For scratch file isolation
        repo_root: Repository root (auto-detected if None)

    Returns:
        Distilled content with noise removed.

    Raises:
        RuntimeError: If subprocess fails.
    """
```

**Note:** Stage 2 is controlled by `USE_LLM_DISTILLATION` flag in `raw_extraction.py` (default: False).

---

## Session Context Orchestration

### collect_session_context

```python
from erk_shared.extraction.session_context import collect_session_context

def collect_session_context(
    git: Git,
    cwd: Path,
    current_session_id: str | None = None,
    min_size: int = 1024,
    limit: int = 20
) -> SessionContextResult | None:
    """Main orchestrator - combines discovery, selection, and preprocessing.

    Workflow:
    1. Get current session ID (auto-detect if not provided)
    2. Find project directory
    3. Get branch context
    4. Discover available sessions
    5. Auto-select based on branch context
    6. Preprocess selected sessions to XML
    7. Combine multiple sessions into single XML

    Args:
        git: Git interface (from ErkContext)
        cwd: Current working directory
        current_session_id: Override auto-detection
        min_size: Minimum session size for discovery
        limit: Maximum sessions to discover

    Returns:
        SessionContextResult with combined_xml, session_ids, branch_context.
        Returns None if:
        - No project directory found
        - No current session ID available
        - No sessions discovered
        - All sessions empty after preprocessing
    """
```

---

## Raw Extraction Plan Creation

### create_raw_extraction_plan

```python
from erk_shared.extraction.raw_extraction import create_raw_extraction_plan

def create_raw_extraction_plan(
    github_issues: GitHubIssues,
    git: Git,
    repo_root: Path,
    cwd: Path,
    current_session_id: str | None = None,
    min_size: int = 1024
) -> RawExtractionResult:
    """Create extraction plan GitHub issue with session context.

    Workflow:
    1. Collect session context via collect_session_context()
    2. Optionally apply Haiku distillation (Stage 2) if enabled
    3. Render via render_session_content_blocks() (handles chunking)
    4. Create GitHub issue with plan template
    5. Post chunked session content as additional comments

    Args:
        github_issues: GitHub issues interface
        git: Git interface
        repo_root: Repository root path
        cwd: Current working directory
        current_session_id: Override auto-detection
        min_size: Minimum session size

    Returns:
        RawExtractionResult with success status, issue URL, chunks count.
    """
```

---

## GitHub Metadata (Session Content Rendering)

### render_session_content_blocks

```python
from erk_shared.github.metadata import render_session_content_blocks

def render_session_content_blocks(
    content: str,
    *,
    session_label: str | None = None,
    extraction_hints: list[str] | None = None,
    max_chunk_size: int = 64536
) -> list[str]:
    """Render session content as GitHub comment blocks.

    Features:
    - Automatic chunking for GitHub's 65536 byte limit
    - Line-aware splitting
    - Chunk numbers for multi-chunk content
    - Collapsible details blocks

    Args:
        content: Session XML content
        session_label: Label (e.g., branch name)
        extraction_hints: Hints for extractors
        max_chunk_size: Maximum chunk size (default: 64536)

    Returns:
        List of formatted comment blocks (as markdown).
    """
```

### chunk_session_content

```python
from erk_shared.github.metadata import chunk_session_content

def chunk_session_content(
    content: str,
    max_chunk_size: int = 64536
) -> list[str]:
    """Split session content into chunks for GitHub comments.

    Features:
    - Line-aware splitting (doesn't break mid-line)
    - Respects GitHub's 65536 byte limit
    - Safety buffer of ~1000 bytes

    Returns:
        List of content chunks.
    """
```

### extract_session_content_from_comments

```python
from erk_shared.github.metadata import extract_session_content_from_comments

def extract_session_content_from_comments(
    comments: list[str]
) -> tuple[str | None, list[str]]:
    """Extract and combine chunked session content from GitHub comments.

    Args:
        comments: List of comment bodies

    Returns:
        Tuple of (combined_session_xml, list_of_session_ids).
        Returns (None, []) if no session content found.
    """
```

---

## Scratch Storage

### get_scratch_dir

```python
from erk_shared.scratch import get_scratch_dir

def get_scratch_dir(
    session_id: str,
    *,
    repo_root: Path | None = None
) -> Path:
    """Get or create session-scoped scratch directory.

    Location: .erk/scratch/sessions/<session-id>/

    Args:
        session_id: Session ID for isolation
        repo_root: Repository root (auto-detected if None)

    Returns:
        Path to scratch directory (created if needed).
    """
```

### write_scratch_file

```python
from erk_shared.scratch import write_scratch_file

def write_scratch_file(
    content: str,
    *,
    session_id: str,
    suffix: str = ".txt",
    prefix: str = "scratch-",
    repo_root: Path | None = None
) -> Path:
    """Write content to session-scoped scratch file.

    Args:
        content: File content
        session_id: Session ID for isolation
        suffix: File extension
        prefix: Filename prefix
        repo_root: Repository root (auto-detected if None)

    Returns:
        Path to created file.
    """
```

### cleanup_stale_scratch

```python
from erk_shared.scratch import cleanup_stale_scratch

def cleanup_stale_scratch(
    *,
    max_age_seconds: int = 3600,
    repo_root: Path | None = None
) -> int:
    """Remove stale session scratch directories.

    Args:
        max_age_seconds: Maximum age before cleanup (default: 1 hour)
        repo_root: Repository root (auto-detected if None)

    Returns:
        Number of session directories cleaned up.
    """
```

---

## Example Usage

### Basic Session Listing

```python
from pathlib import Path
from erk_shared.extraction.session_discovery import (
    get_current_session_id,
    find_project_dir,
    discover_sessions,
)

# Get current session
session_id = get_current_session_id()

# Find project directory
project_dir = find_project_dir(Path.cwd())
if project_dir is None:
    print("No Claude project found")
    exit(1)

# Discover sessions
sessions = discover_sessions(
    project_dir,
    current_session_id=session_id,
    min_size=1024,
    limit=10
)

for s in sessions:
    marker = " (current)" if s.is_current else ""
    print(f"{s.session_id[:8]} - {s.size_bytes} bytes{marker}")
```

### Full Extraction Workflow

```python
from pathlib import Path
from erk_shared.extraction.session_context import collect_session_context
from erk_shared.github.metadata import render_session_content_blocks

# Assumes ctx is an ErkContext
result = collect_session_context(
    git=ctx.git,
    cwd=ctx.cwd,
    min_size=1024
)

if result is None:
    print("No sessions to extract")
    exit(1)

print(f"Collected {len(result.session_ids)} sessions")
print(f"Branch: {result.branch_context.current_branch}")

# Render for GitHub
blocks = render_session_content_blocks(
    result.combined_xml,
    session_label=result.branch_context.current_branch
)

print(f"Generated {len(blocks)} comment blocks")
```
