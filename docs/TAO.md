# The TAO of `erk`

`erk` is a CLI tool built for the orchestration and management of plan-oriented agentic engineering.

## What is Plan-Oriented Agentic Engineering?

AI is transforming software development. What started with in-IDE copilots, intelligent typeaheads, and standalone conversational chat interfaces is now evolving into an entire new generation of tooling.

Planning has become an increasingly important modality. Widely popularized by Claude Code, it is now getting incorporated into other popular tools such as Cursor.

`erk` believes that planning is the foundational skill of agentic engineering and will remain essential for the foreseeable future, even as model capabilities increase.

Planning enables larger units of work to execute with higher quality outcomes. This property also means massive increases in throughput through parallelization. Without planning, you are limited to making serial chains of work more productive via typeaheads or synchronous code generation steps.

More problematically, without planning you are unlikely to provide sufficient context to a model, leaving your instructions too open for interpretation. This is often interpreted as a hallucination. But the reality is that if insufficient context was given, there is no way for the model to fulfill your requirements: It will be forced to invent them.

Put another way: no matter how powerful they become, models cannot solve the "Garbage-In-Garbage-Out" problem. Planning is the right tool in professional software engineering to ensure that the right context is provided to the agent.

## The Gap: No Engineering Process, Tooling, or Workflows Around Plans

Claude Code popularized "plan mode" as a first-class capability in agentic engineering tools. Other tools, such as Cursor and Windsurf, have since followed suit. The ecosystem clearly sees a lot of uptake and progress in the technique.

Yet despite this recognition, planning remains poorly integrated into actual developer workflows in practice. The primitives exist, but there is no coherent process that ties them together.

Engineers who want to work in a plan-oriented way face significant friction. Plans are saved as markdown files and must be managed manually, or exist only ephemerally in agent context. There is no system of record. Plans cannot be queried, tracked, or closed. They are not attached to any automation or workflow.

Parallel execution is similarly ad-hoc. Git worktrees provide isolation, but management around them is primitive and tedious. Developers have to manually bookkeep locations, environments, and so forth.

Many tools and companies working on parts of this problem, but usually in a way that is more about "vibecoding" rather than professional software engineering. Siloed tools, poor integration with native engineering workflows, and lack of true automation are non-starters for engineers working on at-scale, complex systems.

This is a solveable problem. It just requires a renewed embrace of engineering process and better tools.

## The Solution: `erk`

`erk` is a tool centered around an opinionated workflow that unifies plans, worktrees, and compute into a coherent engineering process. It is uncompromisingly plan-oriented: you create plans, you implement plans, and complete plans, often without touching an IDE.

### Plans as System of Record

In `erk`, plans are not files on disk or ephemeral context in an agent session. They are persisted in a system of record. In this initial version, that system is GitHub issues. This means plans:

- Can be saved, listed, and tracked for bookkeeping
- Integrate directly into engineering workflows such as code review
- Can be opened, closed, and attached to pull requests
- Are hubs of context that build up the memory of an engineering organization

### Worktrees Are First-Class

Worktrees are essential to high-output agentic engineering. Without worktrees (or a similar abstraction), you cannot parallelize work across multiple agents, eliminating much of the promise of the technology.

`erk` believes that worktrees should be as first-class as branches in modern engineering workflows. The only reason they aren't right now is tooling quality.

In tools like `git` and `gt`—which `erk` is built on—you checkout branches. In `erk`, you checkout worktrees, which are created ephemerally and tied to a _branch_ and an _environment_.

In the initial version, the toolchain is `gt`, `git`, `uv` (Python environment management), and `gh` (for issues and automation). When you checkout a worktree, it creates or switches to:

- A worktree
- A branch
- A virtual environment (which it syncs and activates)

Additionally there is _typically_ a single plan associated with that worktree.

With those things in place, agents can author code in parallel in an orderly, controlled fashion. The process is seamless.

With `erk` creating a worktree, switching between them, and activating the correct environment happens seamlessly—as easily as checking out a branch. `erk` integrates with Graphite for stacked PRs and uv for instant virtual environment activation. The friction that normally prevents parallel local execution is removed.

### Compute

Agents need compute and environments to autonomously and safely execute in parallel.

By default, `erk` provides isolation at the worktree and virtual environment level on your machine. This enables parallelization but does not solve security and safety issues. Each agent has full access to the file system, and most agentic systems have permissions in place to prompt users when potentially destructive operations could occur. This severely limits autonomy.

Remote, sandboxed execution is the solution to this. In those environments the coding agents can operate in "dangerous" mode and bypass the permission system entirely. `erk` supports this natively.

As an initial remote execution engine, `erk` uses GitHub Actions. You can submit work to the `erk` queue as easily as executing on your own machine. You are no longer limited by monitoring permissions (just turn them off) nor are you limited by the compute capacity of your laptop (you can infinitely scale).
You are only limited by your ability to generate plans and manage workflows.

## Putting It All Together: The Workflow

**Plan → Save → Implement → Review and Iterate → Ship**

1. **Plan:** Within an agentic tool—in this case, Claude Code—you construct a plan. This is where context leaves your head and enters the system.

2. **Save:** The plan is saved to the system of record. In `erk`, this is a slash command within `claude` that creates a tool-managed GitHub issue. The plan is now trackable, queryable, and attached to your engineering workflow.

3. **Implement:** Execute the plan locally with `erk implement` or dispatch it remotely with `erk plan submit`. Local execution creates a worktree, activates the environment, and invokes `claude`. Remote execution triggers a `gh` action that creates a PR. All of this is tracked and managed by `erk`.

4. **Review and Iterate:** Review the code. If the output is close but not complete, comment on the PR use that to bootstrap a follow up coding session. You can seamlessly check out the worktree locally and iterate.

5. **Ship:** Merge the PR. The plan closes automatically, leaving the issue and the PR as a permanent record of what was planned, what was done, and any discussion along the way. Clean up your mess and build up the engineering organization's memory over time.

## Current Scope

`erk` is an internal tool developed at Dagster Labs. It reflects our beliefs about how agentic engineering should work and how we want to work ourselves.

The philosophy is general, but the current implementation is opinionated and specific. To use `erk` effectively today, you need:

- `python`: Programming Language
- `claude`: Claude Code
- `uv`: Fast Python Environment Management
- `gt`: Graphite for stacked PRs
- `gh`: Github for issues, PRs, and Actions

This is the toolchain we use internally. `erk` is designed to be extensible to other languages, systems of record, and compute backends. Our next toolchain will be TypeScript-focused. Beyond that, we have no plans for additional stacks.

If you're outside Dagster Labs and find this useful, you're welcome to explore, but you will likely have challenges using the tool in your environment.

This is also meant to be a showcase and a place to interact with collaborators where we have deep partnerships and context. For the broader public, we will not actively fix bugs, work on features, or accept contributions that do not directly apply to the work at Dagster Labs.
