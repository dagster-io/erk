# Help Text Parsing Patterns

This reference provides practical guidance for extracting information from CLI help text, manual pages, and command output. Different CLI tools use different conventions, and this guide helps navigate that diversity.

## Common Help Text Invocation Patterns

### Standard Help Flags

Try these patterns in order when introspecting a CLI tool:

1. **Long form help**: `<command> --help`
2. **Short form help**: `<command> -h`
3. **Help subcommand**: `<command> help`
4. **Help topic**: `<command> help <topic>`
5. **No arguments**: `<command>` (some tools show help when called without args)
6. **Version flag**: `<command> --version` or `-V` (reveals tool identity and version)

### Subcommand Help Discovery

**For tools with subcommands:**

```bash
# List all subcommands
<command> --help
<command> help

# Get help for specific subcommand
<command> <subcommand> --help
<command> help <subcommand>

# Nested subcommands
<command> <subcommand> <sub-subcommand> --help
```

**Examples:**

- `git --help` → lists subcommands
- `git commit --help` → specific subcommand help
- `gh pr create --help` → nested subcommand help

### Interactive Help Systems

Some CLIs provide interactive help:

- **Man page integration**: `man <command>`, `man <command>-<subcommand>`
- **Info pages**: `info <command>` (GNU tools)
- **Built-in pagers**: Some tools automatically page long help output
- **TUI help**: Some modern CLIs provide interactive help browsers

## Help Text Structure Patterns

### GNU-Style Long Help

**Characteristics:**

- Detailed option descriptions
- Both short and long forms: `-v, --verbose`
- Grouped by category
- Often includes examples at end

**Example structure:**

```
Usage: command [OPTIONS] [ARGUMENTS]

Description of what the command does.

Options:
  -h, --help           Display this help message
  -v, --verbose        Enable verbose output
  -o, --output FILE    Write output to FILE
  -f, --force          Force operation without confirmation

Examples:
  command file.txt
  command -v -o output.txt input.txt
```

### BSD-Style Terse Help

**Characteristics:**

- Minimal descriptions
- Often single-letter flags only
- Compact format
- Reference to man page for details

**Example structure:**

```
usage: command [-hv] [-o file] input

See man command for details.
```

### Modern CLI Help

**Characteristics:**

- Colored output (when TTY detected)
- Clear section headers
- Examples-first approach
- Links to web documentation
- Subcommand-oriented

**Example structure:**

```
GitHub CLI - Work with GitHub from the command line

USAGE
  gh <command> <subcommand> [flags]

CORE COMMANDS
  pr:       Manage pull requests
  issue:    Manage issues
  repo:     Manage repositories

FLAGS
  --help    Show help for command

LEARN MORE
  Use 'gh <command> --help' for more information about a command.
  Read the manual at https://cli.github.com/manual
```

## Extraction Patterns

### Identifying Command Structure

**Flat command structure:**

- Single-level commands (e.g., `ls`, `grep`, `curl`)
- All options at one level
- Pattern: `command [OPTIONS] [ARGUMENTS]`

**Subcommand structure (Noun-Verb):**

- Resource-first hierarchy
- Pattern: `command <resource> <action> [OPTIONS]`
- Example: `gh pr create`, `gh issue list`

**Subcommand structure (Verb-Noun):**

- Action-first hierarchy
- Pattern: `command <action> <resource> [OPTIONS]`
- Example: `docker run container`, `kubectl create deployment`

**Hybrid structure:**

- Mix of flat and subcommands
- Pattern: `command [global-options] <subcommand> [subcommand-options]`
- Example: `git --git-dir=<path> commit -m "message"`

### Parsing Options and Flags

**Option formats to recognize:**

1. **Short flags**: `-h`, `-v`, `-f`
2. **Long flags**: `--help`, `--verbose`, `--force`
3. **Flags with values**: `-o file`, `--output=file`, `--output file`
4. **Boolean flags**: `--flag` or `--no-flag`
5. **Repeated flags**: `-vvv` (increasing verbosity)
6. **Combined short flags**: `-abc` (equivalent to `-a -b -c`)

**Extraction regex patterns:**

```regex
# Short flag with description
-([a-zA-Z]),?\s+--([a-z-]+)\s+(.+)

# Long flag only
--([a-z-]+)\s+(.+)

# Flag with value placeholder
-([a-zA-Z])\s+<([A-Z_]+)>
--([a-z-]+)=?<([A-Z_]+)>
```

### Extracting Subcommands

**Look for section headers:**

- "COMMANDS", "SUBCOMMANDS", "AVAILABLE COMMANDS"
- "CORE COMMANDS", "ADDITIONAL COMMANDS"
- Grouped by category (e.g., "Repository Commands", "Issue Commands")

**Subcommand format patterns:**

```
COMMAND       DESCRIPTION
create        Create a new resource
list          List all resources
delete        Delete a resource
```

**Nested subcommand patterns:**

```
gh pr create        Create a pull request
gh pr list          List pull requests
gh pr view          View a pull request
gh issue create     Create an issue
gh issue list       List issues
```

### Identifying Examples

**Common example section headers:**

- "EXAMPLES", "Example:", "Usage examples:"
- "COMMON USES", "Typical usage:"
- Often at end of help text

**Example patterns to extract:**

```bash
# Comment explaining what this does
$ command arg1 arg2

# Another example with output
$ command --flag value
output line 1
output line 2

# More complex example
$ command | other-command
```

**Look for:**

- Lines starting with `$` or `#` (shell convention)
- Indented command blocks
- Inline comments explaining purpose
- Expected output or results

### Extracting Option Arguments

**Argument placeholder conventions:**

- `<REQUIRED>` - Angle brackets = required argument
- `[OPTIONAL]` - Square brackets = optional argument
- `FILE` - All caps = placeholder name
- `...` - Ellipsis = repeatable argument
- `<file>...` - Required, repeatable
- `[files...]` - Optional, repeatable

**Common placeholder names:**

- `<FILE>`, `<PATH>`, `<DIR>` - File system locations
- `<URL>`, `<URI>` - Network locations
- `<NAME>`, `<ID>` - Identifiers
- `<VALUE>`, `<STRING>`, `<NUMBER>` - Data types
- `<COMMAND>`, `<SUBCOMMAND>` - Nested commands

## Manual Page Parsing

### Man Page Sections

Standard man page structure:

1. **NAME** - Command name and brief description
2. **SYNOPSIS** - Usage syntax
3. **DESCRIPTION** - Detailed explanation
4. **OPTIONS** - Flag and argument descriptions
5. **EXAMPLES** - Usage examples
6. **SEE ALSO** - Related commands
7. **AUTHOR** - Attribution
8. **BUGS** - Known issues

### Extracting from Man Pages

**Accessing man pages:**

```bash
# View man page
man <command>

# Export to text
man <command> | col -b > command_man.txt

# Search man page sections
man -k <keyword>

# Section-specific (1=user commands, 8=admin commands)
man 1 <command>
```

**Man page parsing patterns:**

```bash
# Extract synopsis
man <command> | grep -A 10 "^SYNOPSIS"

# Extract description
man <command> | grep -A 50 "^DESCRIPTION"

# Extract options
man <command> | grep -A 100 "^OPTIONS"
```

### Troff/Groff Format

Man pages use troff formatting. Key markers:

- `.TH` - Title heading
- `.SH` - Section heading
- `.B` - Bold text (often command/option names)
- `.I` - Italic text (often arguments)
- `.BI` - Bold-italic alternating

**Convert to readable format:**

```bash
# Convert troff to plain text
man <command> | col -bx

# Or use man2html for HTML output
man <command> | man2html
```

## GitHub Repository Analysis

### Repository Structure to Examine

**Documentation locations:**

1. `README.md` - Primary documentation, quick start
2. `docs/` or `doc/` - Detailed documentation
3. `examples/` - Usage examples
4. `CONTRIBUTING.md` - Development patterns
5. `man/` - Man page sources
6. `completions/` - Shell completion scripts (reveal command structure)

**Code locations:**

1. `cli/`, `cmd/`, `src/cli/` - Command implementations
2. `test/`, `tests/` - Test files (reveal common use cases)
3. Main executable entry point - Overall structure
4. Subcommand files - Individual command logic

### Mining Issues and Discussions

**Valuable patterns in issues:**

```bash
# Common questions (indicate unclear documentation)
label:question

# Feature requests (reveal desired workflows)
label:enhancement

# Bug reports (reveal common mistakes/pain points)
label:bug

# Usage examples in comments
```

**Search patterns:**

- "How do I..." - Common user questions
- "Is there a way to..." - Workflow questions
- "Expected behavior" - Mental model insights
- Code snippets in issues - Real-world usage

### Extracting Command Structure from Code

**Common CLI framework patterns:**

**Cobra (Go):**

```go
// File structure reveals commands
cmd/
  root.go           // Root command
  create.go         // create subcommand
  list.go           // list subcommand
  create_user.go    // nested: create user
```

**Click (Python):**

```python
@click.command()
@click.option('--flag', help='Description')
def command(flag):
    """Command description"""
```

**Commander (Node.js):**

```javascript
program
  .command("subcommand <required> [optional]")
  .option("-f, --flag", "Description")
  .action((required, options) => {});
```

**Clap (Rust):**

```rust
App::new("command")
    .subcommand(
        SubCommand::with_name("subcommand")
            .arg(Arg::with_name("flag"))
    )
```

### Test Files as Documentation

Test files often reveal:

1. **Common workflows** - Integration tests show typical usage
2. **Edge cases** - Unit tests reveal boundary conditions
3. **Error scenarios** - Tests show how errors are handled
4. **Expected output** - Assertions show what success looks like

**Look for:**

- `test/`, `tests/`, `*_test.go`, `test_*.py`
- `integration/`, `e2e/` - End-to-end scenarios
- Fixture files - Example input data
- Mock outputs - Expected results

## Introspection Strategy

### Progressive Introspection Workflow

Follow this sequence for comprehensive CLI analysis:

**1. Quick Reconnaissance (5 minutes)**

```bash
# Basic identity
command --version
command --help | head -n 20

# Check if man page exists
man command | head -n 50

# Is it open source?
which command
command --version  # Often includes GitHub URL
```

**2. Command Structure Mapping (10-15 minutes)**

```bash
# Full help text
command --help > help_full.txt

# Identify all subcommands
grep -E "^  [a-z-]+\s+" help_full.txt

# Get help for each subcommand
for cmd in create list delete; do
  command $cmd --help > help_${cmd}.txt
done

# Check for nested subcommands
command subcommand --help | grep -E "^  [a-z-]+"
```

**3. Example Extraction (5-10 minutes)**

```bash
# Extract examples from help
command --help | sed -n '/EXAMPLE/,/^[A-Z]/p'

# Check README for examples (if GitHub repo)
curl https://raw.githubusercontent.com/org/repo/main/README.md |
  sed -n '/## Examples/,/##/p'
```

**4. Man Page Deep Dive (10-15 minutes)**

```bash
# Full man page export
man command > man_command.txt

# Extract key sections
man command | grep -A 50 "^OPTIONS" > options.txt
man command | grep -A 30 "^EXAMPLES" > examples.txt
man command | grep -A 10 "^SEE ALSO" > related.txt
```

**5. GitHub Repository Analysis (20-30 minutes)**

```bash
# Clone repository
git clone --depth 1 https://github.com/org/repo

# Examine structure
tree -L 2 -d repo/

# Find command implementations
find repo/ -name "*command*.go" -o -name "*cli*.py"

# Check documentation
ls repo/docs/
cat repo/README.md

# Browse issues for common patterns
# (via GitHub web interface or gh CLI)
gh issue list --repo org/repo --label question
gh issue list --repo org/repo --label documentation
```

**6. Online Research (15-20 minutes)**

```bash
# Search for tutorials and guides
# (web search or focused queries)

# Look for:
# - Official documentation site
# - Blog posts with advanced usage
# - Video tutorials
# - Stack Overflow common questions
# - Reddit discussions
# - Comparison with similar tools
```

### Synthesis and Organization

After introspection, organize findings:

**1. Core Concepts**

- What domain does this CLI operate in?
- What are the primary abstractions (resources, actions)?
- What mental model does it use?

**2. Command Hierarchy**

- Flat or subcommand structure?
- How are commands organized?
- What's the naming pattern?

**3. Common Workflows**

- What are the 5-10 most common tasks?
- What's the quickstart workflow?
- What's the advanced user workflow?

**4. Integration Points**

- What other tools does it work with?
- What file formats does it use?
- What protocols or APIs does it interface with?

**5. Pain Points and Gotchas**

- What do users commonly misunderstand?
- What are the most reported issues?
- What operations are risky or destructive?

## Special Cases

### GUI-First Tools with CLI

Some tools have CLI as secondary interface:

- Help may be minimal
- Documentation may focus on GUI
- CLI may be underdocumented
- Look for `--batch` or `--non-interactive` modes

**Strategy:**

- Focus on what CLI enables that GUI doesn't
- Document automation use cases
- Clarify when CLI is preferred

### Legacy Tools

Older CLI tools may have:

- Inconsistent flag conventions
- Minimal help text
- Man pages as primary documentation
- Idiosyncratic behavior

**Strategy:**

- Emphasize man page content
- Note deviations from modern conventions
- Document common gotchas
- Provide modernization tips (aliases, wrappers)

### API-Wrapper CLIs

CLI tools wrapping REST APIs:

- Commands often mirror API endpoints
- JSON output common
- Authentication patterns important

**Strategy:**

- Map CLI commands to API operations
- Document authentication flow
- Show JSON output examples
- Note API-specific limitations

## Quality Checks

Before finalizing CLI introspection, verify:

- [ ] Captured all top-level commands/subcommands
- [ ] Documented most common flags for each command
- [ ] Extracted representative examples
- [ ] Identified command structure pattern (flat/nested, noun-verb/verb-noun)
- [ ] Noted integration points with other tools
- [ ] Captured mental model and core concepts
- [ ] Documented any gotchas or common mistakes
- [ ] Verified information accuracy (tested commands)
- [ ] Noted CLI version examined
- [ ] Linked to authoritative documentation

## Tips for Difficult-to-Parse CLIs

**When help text is poorly structured:**

- Fall back to man pages
- Search online documentation
- Browse GitHub issues for clarification
- Test commands directly to understand behavior

**When documentation is minimal:**

- Focus on code reading (if open source)
- Community resources (blogs, StackOverflow)
- Direct experimentation in safe environment
- Document discovered behaviors

**When tool is closed-source:**

- Rely on official documentation
- Community knowledge bases
- Trial and error with safe operations
- Document observed behavior patterns

---

## Key Takeaway

Different CLI tools use vastly different help text conventions. Successful introspection requires:

1. **Flexibility** - Try multiple help invocation patterns
2. **Multiple sources** - Combine help text, man pages, README, code
3. **Testing** - Verify understanding by running commands
4. **Synthesis** - Organize findings into coherent mental model

The goal is comprehensive understanding, not just command listing. Focus on helping future users build mental models, not just providing a command reference.
