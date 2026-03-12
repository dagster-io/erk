---
title: The pr-address workflow 
description: erk incorporates code review directly in your agentic engineering workflow
---
`erk` can query GitHub code reviews for unresolved comments and discussions, addresses them locally, and resolves them—all within your agentic workflow. In a world of AI-assisted authoring and code review, PR feedback volume can be high. This workflow manages that workload while leaving you in total control.

### Addressing Feedback

When on a branch associated with a PR, run `/erk:pr-address` from within Claude (slash command), or `erk pr address` from the command line—they are equivalent. The CLI version launches Claude interactively.

Once launched, the workflow does the following:

1. Queries the PR for all unresolved threads and discussions and downloads them for analysis.
2. Classifies and batches them by disposition and complexity, then presents them to you.
3. Processes each batch as a self-contained cycle: apply fixes, run CI, commit, resolve threads, and report progress. (See [Categorization Details](#categorization-details) for the full breakdown.)

After all batches complete, the classifier re-runs to verify nothing was missed, the PR description is updated, and you get push instructions.

#### Previewing Feedback

You can _preview_ the feedback from within Claude without acting on it. This is useful when you want to see how comments will be categorized and batched before deciding whether to proceed. Run `/erk:preview-pr-address` to do this.

#### Plan Mode

For complex feedback that would require substantial changes, you can run `/erk:pr-address` while in Plan Mode. Rather than executing fixes, Claude will present a plan for addressing all the feedback, giving you a chance to review the approach before committing to it.

### Use Cases

#### Bots

With AI code review assistance on the rise, the amount of noise in PRs is increasing. While individual bot comments can provide value, it is easy to become overwhelmed.

The address workflow is designed to manage this, particularly through the batching mechanism, which groups repetitive feedback together, addresses the concerns, and resolves them in bulk.

`erk` also comes with its own lightweight code review system described later. It is designed to work hand-in-hand with the address workflow.

#### Self-Review

This workflow is also an excellent way to manage your own review process. With agents, there is often high latency between authoring code and looking at it again, and you are often managing more changes per PR than before.

You can treat the code review as a continuation of your session, directly prompting your local agent through the code review UI. This is often easier than navigating an IDE or trying to remember what files have been edited, where, and the surrounding context from within a non-visual TUI.

The workflow is:

* Author the PR.
* Review the PR yourself, leaving comments and discussions where appropriate.
* Run the pr-address workflow locally.

Another use case is reviewing remote coding workflows that have never been present on your machine. A PR is a useful way to review code written by an agent that you will be accountable for.

#### Fellow Humans 

Naturally you can use this to address feedback from your fellow human collaborators. We don't recommend doing this blindly, except for trivial, uncontroversial feedback. That said, as usage of the system becomes more universal within an org, you may find that collaborators begin writing prompts for you to execute on your local copy, effectively turning the code review into a collaborative, agentic coding session.


#### System of record for feedback and best practices.

Beyond the efficiency gains of channeling all feedback through code review and tracking resolution, the system captures valuable context on how humans and agents interact with the codebase. You can mine this information to get insights about contributors, agents, code review systems, and the state of your best practices. Mining this information to construct or edit skills that can steer subsequent authoring and review sessions is high leverage.

### Categorization Details

The workflow has two phases: **classify**, then **execute**.

#### Classification

Classification fetches every unresolved comment on the PR—inline review threads and discussion comments alike—and assigns each one two labels:

- **Disposition**
  - **Actionable**: requires code changes.
  - **Informational**: an optional suggestion that does not require code changes. Presented to you individually so you can accept or dismiss.
  - **Pre-existing**: flagged in moved or renamed code, not newly introduced.
- **Complexity**: **local**, **single-file**, **cross-cutting**, or **complex**.

#### Execution

Comments are grouped into ordered batches by complexity and processed from simplest to hardest.

- Simple batches (pre-existing dismissals, local fixes, and single-file changes) proceed automatically.
- Cross-cutting and complex batches pause and request your approval before any changes are made.
- Informational comments are shown to you individually so you can choose to accept or dismiss them.

Each batch is a self-contained cycle: apply fixes, run CI, commit, resolve the GitHub threads, and report progress. False positives are given an explanatory reply and resolved without code changes.



### Reference

* `pr-address`
* `preview-pr-address`