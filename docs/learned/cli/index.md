<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Cli Documentation

- **[activation-scripts.md](activation-scripts.md)** — working with worktree environment setup, understanding .erk/activate.sh scripts, configuring post-create commands, implementing deferred execution patterns
- **[ambiguity-resolution.md](ambiguity-resolution.md)** — implementing CLI commands that accept identifiers with multiple possible matches, designing CLI behavior for ambiguous input, displaying tables of options without interactive selection
- **[checkout-helpers.md](checkout-helpers.md)** — writing checkout commands, creating worktrees in checkout commands, implementing branch checkout logic
- **[command-group-structure.md](command-group-structure.md)** — creating a new command group, adding commands to an existing group, understanding command file organization
- **[command-organization.md](command-organization.md)** — organizing CLI commands, understanding command structure, designing command hierarchies
- **[docker-isolation.md](docker-isolation.md)** — running erk implement with --docker flag, building the erk-local Docker image, understanding Docker volume mounts for Claude Code
- **[fast-path-pattern.md](fast-path-pattern.md)** — implementing CLI commands that can skip expensive operations, adding fast path optimization to existing commands, understanding when to invoke Claude vs complete locally
- **[json-schema.md](json-schema.md)** — adding --json flag to CLI commands, parsing JSON output from erk commands, implementing kit CLI commands with JSON output
- **[list-formatting.md](list-formatting.md)** — formatting list output, designing list commands, ensuring consistent list display
- **[optional-arguments.md](optional-arguments.md)** — making a CLI argument optional, inferring CLI arguments from context, implementing branch-based argument defaults
- **[output-styling.md](output-styling.md)** — styling CLI output, using colors in CLI, formatting terminal output
- **[template-variables.md](template-variables.md)** — configuring .env templates, using substitution variables in config.toml
