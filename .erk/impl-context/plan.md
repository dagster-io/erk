# Context

The `refac-mock-to-fake` skill guides agents to find the right gateway abstraction when replacing `unittest.mock.patch`. The current guidance says "don't stop at the lowest-level gateway" but doesn't make explicit that `subprocess.run` is *itself* too low-level to be the gateway boundary. Agents following the skill might create a gateway that wraps `subprocess.run` generically — which just moves the mock one step up without gaining the right abstraction.

The correct principle (which the user articulated) is: **the gateway abstraction should be named after the utility/CLI tool being invoked, not after the underlying mechanism.** For example:

- `gh pr view` calls → a `GhCli` or `LocalGitHub` gateway, not a "subprocess" gateway
- `cmux new-workspace` calls → a `CmuxGateway`, not a "shell runner" gateway

This mirrors how existing gateways work: `LocalGitHub` wraps `gh` calls, `Git` wraps `git` calls, etc.

Two locations need updating:
1. **`refac-mock-to-fake` skill** — Phase 2 and pitfalls need the explicit "subprocess is too low-level" principle
2. **`docs/learned/architecture/gateway-abc-implementation.md`** — add a tripwire reinforcing this

---

# Plan

## 1. Update `refac-mock-to-fake` SKILL.md

File: `.claude/skills/refac-mock-to-fake/SKILL.md`

**In Phase 2 "Gateway Discovery"**, add an explicit callout box or bold rule after the intro paragraph:

> **Rule: `subprocess.run` is never the right gateway boundary.**
> The gateway should be named after the *tool* being invoked (e.g., `GhCli`, `CmuxGateway`, `GitGateway`), not after the underlying mechanism (`subprocess`, `shell`). A gateway that just wraps `subprocess.run` is no better than mocking `subprocess.run` directly — it skips the meaningful abstraction layer.

**In Step 2a "Identify the system boundary"**, update the examples to make the tool-level nature explicit:

- Old: "`shutil.which("claude")` → 'is the Claude CLI installed?'"
- Update the framing: the unit is "interact with the Claude CLI" → gateway is `PromptExecutor` (Claude-specific), not `Shell` (subprocess-generic)

**Add Pitfall 5** to the Common Pitfalls section:

> **Pitfall 5: Creating a subprocess-level gateway**
> If you find yourself designing a gateway called `ShellRunner`, `SubprocessGateway`, or `CommandRunner`, stop. That's still mocking at the wrong level. The gateway must be specific to the *tool* being called:
> - `subprocess.run(["gh", ...])` → `LocalGitHub` or a `GhCli` gateway
> - `subprocess.run(["cmux", ...])` → `CmuxGateway`
> - `subprocess.run(["claude", ...])` → `PromptExecutor`
> - `subprocess.run(["git", ...])` → `Git` gateway
>
> Name the gateway after what it represents, not how it executes.

## 2. Update `gateway-abc-implementation.md`

File: `docs/learned/architecture/gateway-abc-implementation.md`

Add a new tripwire entry in the frontmatter `tripwires:` list:

```yaml
- action: "creating a gateway named ShellRunner, CommandRunner, SubprocessGateway, or similar mechanism-named gateway"
  warning: "Gateway names must reflect the TOOL being wrapped, not the execution mechanism. Use LocalGitHub for gh calls, Git for git calls, CmuxGateway for cmux calls, PromptExecutor for claude calls. A mechanism-named gateway is just moving the mock up one layer without gaining abstraction."
```

Also add a short note in the **Scope** or **Checklist** section under a header like "Naming Gateways":

> Gateways are named after the **tool or service** they wrap, not the **mechanism** used. `subprocess.run` is the mechanism; the gateway is named `Git`, `LocalGitHub`, `CmuxGateway`, etc. If your gateway name ends in `Runner`, `Executor` (unless it's a specific executor like `PromptExecutor`), `Shell`, or `Subprocess`, reconsider the abstraction level.

---

# Verification

1. Read both files after editing to confirm changes are coherent and consistent
2. No tests to run (documentation-only change)
3. Confirm the skill description still accurately triggers the skill when needed
