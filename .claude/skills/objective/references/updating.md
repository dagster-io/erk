# Updating an Objective

See [format.md](format.md) for:

- **Action Comment Template** - What to include in update comments
- **When to Update** - Triggers for updating vs waiting
- **Update Examples** - Real examples of the two-step workflow

## Quick Summary

The two-step pattern applies to ALL objective changes, not just completions:

| Change Type        | Comment                                               | Body Update           |
| ------------------ | ----------------------------------------------------- | --------------------- |
| Complete a node    | "Action: Completed X"                                 | Status → done, add PR |
| Add context        | "Action: Added X"                                     | Add section to body   |
| Refine decision    | "Action: Refined X"                                   | Update decision text  |
| Add phase          | "Action: Added Phase X"                               | Add phase to roadmap  |
| Hit blocker        | "Action: Identified blocker"                          | Status → blocked      |
| Reconcile after PR | "Action: [Title]" with Body Reconciliation subsection | Update stale sections |

**Why both steps?**

- Comment = changelog (when/why things changed)
- Body = source of truth (current complete state)

Comment first (captures the moment), then body (reflects new state).
