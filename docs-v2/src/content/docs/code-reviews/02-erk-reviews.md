---
title: Use erk reviews
description: Erk comes with automated PR content review
---

Erk comes with lightweight review agents that run automatically when a published PR is updated. These agents complement the [pr-address workflow](/code-reviews/02-addressing-review-feedback/)—reviews flag issues, and the author uses address workflow to resolve them.

You can install pre-defined reviews that come with erk (e.g. `dignified-python`) or build your own.

### Adversarial Review

Erk reviews are be designed to be focused and adversarial.

In AI-enabled projects, engineers typically use skills and markdown files to steer and guide authoring agents. While these are helpful, agents frequently violate the guidelines in those files. Models may improve to the point where this is no longer a problem, but for now it is the state of affairs.

We have found that special-purpose review agents, narrowly targeted to find code that violates specific skills, are more effective at ensuring adherence. Their context is free of everything that accumulates prior to and during authoring. With clean context, they can focus exclusively on review and only on the code that has changed. Additionally, this can be done with cheaper, smaller models—critical given that automated code review can rack up massive inference bills.

Many specialized agents also make attribution much accurate. You can see which agent flagged what issue and why. When you observe code that violates your sensibilities, it more clear who should have detected the error, and where to add the rules. These specialized agents are also more straightforward to build evals for that more generalized, ambitious agents.

By using many specialized agents in parallel you get increased speed, lower cost, and more accurate attribution and observability.

### Skill-Based Review

A common pattern is for a review to wrap a skill. For example, the `dignified-python` skill encodes a set of coding standards, and the `dignified-python` reviewer is its counterpart. The reviewer instructs the agent to load the skill files and examine the current diff for violations. It also highlights particularly important rules inline to increase adherence.

- [Addressing review feedback](/code-reviews/02-addressing-review-feedback/) — resolve PR comments using the pr-address workflow
- [Creating a review](/code-reviews/03-creating-a-review/) — add a new automated review to your project
