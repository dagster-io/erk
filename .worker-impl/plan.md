# Extraction Plan: erk-statusline Architecture Guide

## Objective

Document the erk-statusline package architecture to accelerate future statusline modifications.

## Source Information

- **Session ID**: 4dfe5e20-032d-4d83-95b7-1ce5d27047be
- **Raw Materials**: https://gist.github.com/schrockn/dc50fe36847518d1ee2d38fa64ac6680

## Documentation Items

### Item 1: erk-statusline Architecture Guide

**Type**: Category B (Teaching Gap)
**Location**: `docs/learned/architecture/erk-statusline.md`
**Action**: Create new document
**Priority**: High

**Content**:

Create a comprehensive architecture guide covering:

1. **Package Structure**
   - Entry point: `erk_statusline.statusline:main`
   - Key modules: statusline.py, colored_tokens.py, context.py

2. **Token/TokenSeq Pattern**
   - Immutable Token class with color support
   - TokenSeq for composable sequences
   - Color enum for ANSI escape codes
   - Helper functions: context_label(), metadata_label(), hyperlink_token()

3. **Gateway Pattern (StatuslineContext)**
   - Frozen dataclass with Git, GitHub, Graphite, BranchManager gateways
   - Enables testability via dependency injection
   - Created via create_context(cwd)

4. **Parallel GitHub API Fetching**
   - ThreadPoolExecutor for concurrent requests
   - PR details and check runs fetched in parallel
   - 1.5s per-call timeout, 2s executor timeout
   - Error fallback to defaults (never crashes)

5. **Caching Strategy**
   - Cache location: /tmp/erk-statusline-cache/
   - Cache key: SHA256 hash of branch name
   - TTL: 30 seconds
   - Stores: pr_number, head_sha

6. **Data Flow**
   - Input: JSON stdin with workspace/model info
   - Fetch: git status → GitHub data (parallel)
   - Build: TokenSeq from components
   - Output: ANSI-colored string to stdout

### Item 2: Adding New Statusline Entries Pattern

**Type**: Category B (Teaching Gap)
**Location**: `docs/learned/architecture/erk-statusline.md` (section within above doc)
**Action**: Include as section in Item 1
**Priority**: High

**Content**:

Document the 6-step pattern for adding new entries:

1. **Fetch Data** - Create function to fetch from GitHub API (REST or GraphQL)
2. **Update Data Structure** - Add field to GitHubData NamedTuple
3. **Extend Parallel Fetch** - Add to ThreadPoolExecutor in fetch_github_data_via_gateway()
4. **Create Display Function** - Build token/string representation
5. **Integrate into Label** - Add to build_gh_label() or main statusline
6. **Add Tests** - Unit tests for fetch and display functions

Include code examples from existing implementations (check runs, PR details).

## Verification

1. Document created at docs/learned/architecture/erk-statusline.md
2. Document follows learned-docs conventions (frontmatter with read_when)
3. Index updated at docs/learned/index.md
4. Run: erk docs check (if available)

## Related Documentation

- docs/learned/architecture/github-graphql.md - GraphQL patterns
- .claude/skills/dignified-python/ - Python coding standards