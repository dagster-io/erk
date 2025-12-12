# prettier Execution and Parsing Guide

Comprehensive guide for executing prettier commands and parsing formatting results.

## Command Detection

Detect prettier in these command patterns:

```bash
prettier
uv run prettier
make prettier
make prettier-check
```

## Command Patterns

### Basic Invocations

```bash
# Check all files
prettier --check .

# Format all files
prettier --write .

# Check specific pattern
prettier --check "**/*.md"

# Format specific directory
prettier --write src/

# Format specific file
prettier --write src/file.js

# List files that differ
prettier --list-different .
```

### Common Flags

**Check vs Write:**

- `--check` - Check if files are formatted (exit 1 if not)
- `--write` - Format files in place
- `--list-different` - List files that differ from prettier formatting

**File Selection:**

- `--ignore-path PATH` - Path to ignore file
- `--ignore-unknown` - Ignore unknown file extensions
- `--no-editorconfig` - Don't use .editorconfig

**Output:**

- `--loglevel {error,warn,log,debug,silent}` - Log level
- `--color` - Force color output
- `--no-color` - Disable color output

**Configuration:**

- `--config PATH` - Path to config file
- `--no-config` - Ignore config files
- `--config-precedence {cli-override,file-override,prefer-file}` - Config precedence

**Formatting Options (if not in config):**

- `--print-width NUM` - Line width (default: 80)
- `--tab-width NUM` - Tab width (default: 2)
- `--use-tabs` - Use tabs instead of spaces
- `--semi` - Add semicolons (default: true)
- `--single-quote` - Use single quotes (default: false)
- `--trailing-comma {none,es5,all}` - Trailing commas
- `--prose-wrap {always,never,preserve}` - Markdown text wrapping

### Make Targets

```bash
# Project-specific make targets
make prettier          # Format all files
make prettier-check    # Check formatting
```

## Supported Languages

prettier formats many languages:

- **JavaScript/TypeScript**: .js, .jsx, .ts, .tsx, .mjs
- **CSS/SCSS/Less**: .css, .scss, .less
- **HTML**: .html, .htm
- **JSON**: .json, .jsonc
- **Markdown**: .md, .markdown
- **YAML**: .yml, .yaml
- **GraphQL**: .graphql, .gql
- **And more**: .vue, .svelte, .astro, etc.

## Output Parsing Patterns

### Check Mode - All Formatted

```
Checking formatting...
All matched files use Prettier code style!
```

**Extract:**

- Success indicator
- All files properly formatted

### Check Mode - Files Need Formatting

```
Checking formatting...
.claude/agents/runner.md
src/erk/config.py
tests/test_paths.py
Code style issues found in 3 files. Run Prettier with --write to fix.
```

**Extract:**

- Files needing formatting (each on its own line)
- Count: `3 files`
- Instruction to use --write

### Write Mode - Success

```
.claude/agents/runner.md 123ms
src/erk/config.py 45ms
tests/test_paths.py 67ms
```

**Extract:**

- Files formatted (each on line with timing)
- Count of files formatted: `3 files`

### Write Mode - No Changes

```
Checking formatting...
All matched files use Prettier code style!
```

**Extract:**

- No files needed formatting
- Success confirmation

### List Different Mode

```
.claude/agents/runner.md
src/erk/config.py
tests/test_paths.py
```

**Extract:**

- List of files that differ from prettier format
- One file per line

### Syntax Error

```
[error] src/broken.js: SyntaxError: Unexpected token (5:12)
[error]   3 | function test() {
[error]   4 |   const x = {
[error] > 5 |     bad: syntax: here
[error]     |            ^
[error]   6 |   }
[error]   7 | }
```

**Extract:**

- File with syntax error
- Error type: `SyntaxError`
- Location: line 5, column 12
- Context showing the error

### No Files Matched

```
No files matching the pattern were found: "**/*.fake"
```

**Extract:**

- Pattern that matched no files
- Warning about empty result

## Parsing Strategy

### 1. Check Exit Code

- `0` = All files formatted correctly (or successfully formatted with --write)
- `1` = Files need formatting (--check) or syntax errors
- `2` = Prettier error or invalid config

### 2. Detect Operation Mode

Look for flags in command:

- `--check`: Check mode (read-only)
- `--write`: Write mode (format files)
- `--list-different`: List mode (show files needing formatting)

### 3. Parse Output Based on Mode

**Check Mode:**

- Success: `All matched files use Prettier code style!`
- Failure: List of file paths + `Code style issues found in X files`

**Write Mode:**

- List of formatted files with timing
- Or success message if no changes needed

**List Mode:**

- List of file paths (one per line)

### 4. Extract File List

Files appear as paths, one per line:

```
path/to/file1.md
path/to/file2.js
```

Count the lines to get file count.

### 5. Handle Errors

Syntax errors have format:

```
[error] file: ErrorType: message (line:col)
```

Extract file, error type, location.

## Make Target Integration

Common make targets in projects:

- `make prettier` - Format all files with --write
- `make prettier-check` - Check all files without writing

When executing via make, parse the underlying prettier output the same way.

## Reporting Guidance

### All Files Formatted (Check)

**Summary**: "All files properly formatted (checked X files)"
**Include**: File count if available
**Omit**: Individual file list

### Files Need Formatting (Check)

**Summary**: "Formatting check failed: X files need formatting"
**Include**:

- List of file paths needing formatting
- Count of files
- Instruction to use --write or make prettier

### Files Formatted Successfully (Write)

**Summary**: "Formatted X files successfully"
**Include**:

- Count of formatted files
- Optionally: timing summary

### No Files Changed (Write)

**Summary**: "All files already properly formatted"

### Syntax Error

**Summary**: "Failed to format due to syntax error"
**Include**:

- File with syntax error
- Error type and location
- Relevant code context

### No Files Matched

**Summary**: "No files matched pattern"
**Include**: Pattern that was used

## Best Practices

1. **Check exit code first** - most reliable indicator
2. **Detect mode from command** - check vs write vs list
3. **Count files from output** - line count of file list
4. **Keep success brief** - just confirmation and count
5. **List all files needing formatting** when check fails
6. **Note syntax errors prominently** - blocking issue
7. **Distinguish "no changes" from "formatted successfully"**

## Example Outputs to Parse

### Example 1: Check Pass

```bash
$ prettier --check .
Checking formatting...
All matched files use Prettier code style!
```

**Parse as**: Success, all files formatted

### Example 2: Check Fail

```bash
$ prettier --check .
Checking formatting...
.claude/agents/runner.md
src/config.py
Code style issues found in 2 files. Run Prettier with --write to fix.
```

**Parse as**: 2 files need formatting: .claude/agents/runner.md, src/config.py

### Example 3: Write Success

```bash
$ prettier --write .
.claude/agents/runner.md 145ms
src/config.py 23ms
```

**Parse as**: Formatted 2 files successfully

### Example 4: Make Target

```bash
$ make prettier-check
prettier --check .
Checking formatting...
All matched files use Prettier code style!
```

**Parse as**: Make target executed prettier, all files formatted
