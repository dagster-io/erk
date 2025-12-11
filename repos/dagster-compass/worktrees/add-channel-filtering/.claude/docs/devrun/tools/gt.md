# gt (Graphite) Execution and Parsing Guide

Comprehensive guide for executing Graphite (gt) commands and parsing output.

## Command Detection

Detect gt in these command patterns:

```bash
gt
gt <command>
gt <command> --flags
```

## Command Patterns

### Basic Invocations

```bash
# Get current branch name
gt branch --name

# Get parent branch
gt parent

# Get children branches
gt children

# Get branch info (parent, children, commit)
gt branch info

# Navigate stack
gt up
gt down
gt top
gt bottom

# Submit PR
gt submit
gt submit --publish --no-edit
gt submit --stack

# Delete branch
gt delete <branch-name>

# View stack
gt log
gt log short
```

### Common Commands

**Branch Information:**

- `gt branch --name` - Current branch name
- `gt parent` - Parent branch name
- `gt children` - Space-separated list of child branches
- `gt branch info` - Complete metadata (parent, children, commit SHA)

**Stack Navigation:**

- `gt up [N]` - Move up stack N times (default 1)
- `gt down [N]` - Move down stack N times (default 1)
- `gt top` - Move to top of stack
- `gt bottom` - Move to bottom of stack

**Stack Management:**

- `gt submit` - Submit current branch as PR
- `gt submit --stack` - Submit entire stack
- `gt submit --publish --no-edit` - Submit without opening editor
- `gt squash` - Squash all commits on branch into one
- `gt restack` - Rebase to ensure parent in history
- `gt sync` - Sync from remote and clean up merged branches

**Branch Operations:**

- `gt delete <branch>` - Delete branch and update metadata
- `gt rename <name>` - Rename current branch
- `gt track <branch>` - Start tracking branch with gt
- `gt untrack <branch>` - Stop tracking branch

**Visualization:**

- `gt log` - Full stack visualization
- `gt log short` - Compact stack visualization
- `gt status` - File status information

## Output Parsing Patterns

### Success Outputs

**gt parent:**

```
feature-branch-parent
```

Extract: Single line with parent branch name

**gt children:**

```
child-1 child-2 child-3
```

Extract: Space-separated list of branch names

**gt branch info:**

```
Branch: feature-branch
Parent: main
Children: child-1, child-2
Commit: abc1234567890abcdef1234567890abcdef12
```

Extract structured fields:

- Branch: current branch name
- Parent: parent branch name
- Children: comma-separated list
- Commit: full commit SHA

**gt submit (success):**

```
✓ Pushed branch feature-branch
✓ Created PR: https://github.com/owner/repo/pull/123
```

Extract: PR URL pattern `https://github.com/.../pull/NNN`

**gt branch --name:**

```
feature-branch
```

Extract: Single line with branch name

**gt log short (display only):**

```
◯ feature-c (3 commits)
◯ feature-b (2 commits)
◯ feature-a (1 commit)
◉ main
```

⚠️ **WARNING**: Only use for display. DO NOT parse for relationships. Use `gt parent`, `gt children`, or `gt branch info` instead.

### Failure Outputs

**Not in repository:**

```
fatal: not a git repository (or any of the parent directories): .git
```

Extract: Error indicating not in git repo

**Branch not found:**

```
Error: branch 'foo' does not exist
```

Extract: Branch name that doesn't exist

**No parent:**

```
Error: no parent branch
```

Extract: Current branch is trunk (has no parent)

**Submit failure:**

```
Error: GitHub API rate limit exceeded
```

Extract: Error reason from GitHub API

### Edge Cases

**Multiple children:**

```
child-1 child-2 child-3 child-4
```

Extract: Parse space-separated list into array

**No children:**

```
(empty output)
```

Extract: Empty list of children

**Commit count = 1:**

```
1
```

Used in squash pre-check - single commit means squash not needed

## Special Handling

### gt squash Pre-execution Check

**Before executing `gt squash`:**

1. Count commits using git command: `git rev-list --count $(gt parent)..HEAD`
2. If count equals 1:
   - DO NOT execute squash command
   - Return success with message: "Branch has only 1 commit - squash not required"
   - Explain no action taken since already in desired state
3. If count is greater than 1:
   - Proceed with executing `gt squash` normally
   - Parse and return squash results

**Rationale**: Squashing a single commit is a no-op and can confuse users. Skip execution and provide clear feedback.

**Implementation**:

```bash
# Get commit count
COMMIT_COUNT=$(git rev-list --count $(gt parent)..HEAD)

# Check if squash is needed
if [ "$COMMIT_COUNT" -eq 1 ]; then
    # Skip squash, report not needed
    echo "Branch has only 1 commit - squash not required"
else
    # Execute squash
    gt squash
fi
```

### gt log short Display Only

**CRITICAL**: `gt log short` output format is counterintuitive and confuses agents when parsed.

**Correct usage:**

- Display tree visualization to users as-is
- Return raw output without parsing relationships

**Incorrect usage:**

- Attempting to parse parent-child relationships from tree
- Using tree symbols to infer branch structure

**For structured data, use instead:**

- `gt parent` - explicit parent branch
- `gt children` - explicit children branches
- `git branch --show-current` - current branch name
- `gt branch info` - complete metadata

## Parsing Strategy

### 1. Check Exit Code

- `0` = Command succeeded
- Non-zero = Command failed

### 2. Identify Command Type

Based on command, determine expected output format:

- Single line: `gt parent`, `gt branch --name`
- Multi-field: `gt branch info`
- Space-separated: `gt children`
- URL extraction: `gt submit`
- Tree visualization: `gt log`, `gt log short`

### 3. Extract Structured Data

**For `gt parent`:**

- Take first line as parent branch name
- Handle empty output (trunk branch has no parent)

**For `gt children`:**

- Split output on whitespace
- Return as list
- Handle empty output (no children)

**For `gt branch info`:**

- Parse each line with format `Key: value`
- Extract: Branch, Parent, Children, Commit
- Handle comma-separated children list

**For `gt submit`:**

- Search for GitHub PR URL patterns
- Extract PR number, owner, repo
- Return full URL

**For `gt log short`:**

- Return raw output for display
- DO NOT parse relationships

### 4. Handle Errors

- Capture stderr output
- Identify error type (not in repo, branch not found, API error)
- Include full error message in response

### 5. Special Pre-checks

**For `gt squash`:**

- Run commit count check first using: `git rev-list --count $(gt parent)..HEAD`
- Skip execution if count = 1
- Return informative success message

## Reporting Guidance

### Get Branch Relationships

**Command**: Multiple commands executed

- `git branch --show-current`
- `gt parent`
- `gt children`

**Output**:

```markdown
**Current branch**: feature-branch
**Parent branch**: main
**Children branches**: child-1, child-2
```

### Submit Branch as PR

**Command**: `gt submit --publish --no-edit`

**Success output**:

```markdown
**PR created**: https://github.com/owner/repo/pull/123
**Branch**: feature-branch
```

### Squash with Single Commit

**Pre-check**: `git rev-list --count $(gt parent)..HEAD` returns `1`

**Command**: `gt squash` (skipped due to pre-check)

**Output**:

```markdown
Branch has only 1 commit - squash not required

The current branch already has a single commit. Squashing is only needed when there are multiple commits to combine. No action was taken.
```

### Squash with Multiple Commits

**Command**: `gt squash`

**Success output**:

```markdown
Successfully squashed 3 commits into 1
```

### Command Failure

**Command**: `gt parent`

**Error output**:

```markdown
Error: no parent branch

The current branch is trunk and has no parent.
```

### Timeout

**Command**: `gt submit --stack` (timeout after 60s)

**Output**:

```markdown
Command exceeded 60-second timeout while processing branch-3.
Partial results: 2 PRs created successfully before timeout.
Main agent should retry remaining branches or investigate repository performance.
```

## Best Practices

### Output Reporting

**Success (simple commands):**

- 2-3 sentences with key info
- Omit raw output if parsed successfully

**Success (complex commands):**

- Structured summary with parsed data
- Include raw output if helpful

**Failures:**

- Full error message
- Context about what went wrong
- Relevant stderr output

**Raw output inclusion:**

- Include for failures (always)
- Include if output is short (< 50 lines)
- Include if parsing was ambiguous
- Omit for simple successful commands with clear parsed output
- Truncate if very long (> 50 lines): first 10 + last 10 lines

### Command Execution

1. **Preserve command exactly** - don't modify user's command
2. **Set timeout to 60 seconds** - some gt commands can be slow
3. **Capture stdout and stderr** - both contain useful info
4. **Check exit codes** - most reliable success indicator
5. **Run special pre-checks** - gt squash commit count check using git command

### Parsing Guidelines

1. **Use explicit commands** - prefer `gt parent` over parsing `gt log`
2. **Handle empty output** - trunk has no parent, leaf has no children
3. **Extract URLs carefully** - look for full GitHub PR URL patterns
4. **Don't parse tree visualizations** - use structured commands instead
5. **Validate extracted data** - branch names shouldn't have special characters
