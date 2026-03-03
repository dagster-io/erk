# Update plan-save output: hierarchical Implement/Checkout format

## Context

The current plan-save output uses "Same slot" / "New slot" section headers with "Local:" and "Implement:" sub-labels. This is unclear:
- "Local" doesn't communicate what it does
- The section headers add noise without aiding comprehension
- `erk implement --dangerous` is the only option; users can't easily run without `--dangerous`

The new format:
- Groups by action (Implement first, then Checkout)
- Uses self-describing labels ("Here" / "In new wt")
- Provides both safe and dangerous implement variants
- Drops section headers — the label hierarchy carries the meaning

## File to change

**`.claude/commands/erk/plan-save.md`** — lines 171–220 (slot options block + next steps block)

## Changes

### Slot options block (lines 175–205)

Replace both trunk/non-trunk variants.

**On trunk = true** (new-wt recommended → "In new wt" listed first):

```
OR exit Claude Code first, then run one of:

Implement plan #<plan_number>:
  In new wt:        source "$(erk br co --new-slot --for-plan <plan_number> --script)" && erk implement
    (dangerously):  source "$(erk br co --new-slot --for-plan <plan_number> --script)" && erk implement -d
  Here:             source "$(erk br co --for-plan <plan_number> --script)" && erk implement
    (dangerously):  source "$(erk br co --for-plan <plan_number> --script)" && erk implement -d

Checkout plan #<plan_number>:
  In new wt:  erk br co --new-slot --for-plan <plan_number>
  Here:       erk br co --for-plan <plan_number>

Dispatch to queue: erk pr dispatch <plan_number>
```

**On trunk = false** (same slot recommended → "Here" listed first):

```
OR exit Claude Code first, then run one of:

Implement plan #<plan_number>:
  Here:             source "$(erk br co --for-plan <plan_number> --script)" && erk implement
    (dangerously):  source "$(erk br co --for-plan <plan_number> --script)" && erk implement -d
  In new wt:        source "$(erk br co --new-slot --for-plan <plan_number> --script)" && erk implement
    (dangerously):  source "$(erk br co --new-slot --for-plan <plan_number> --script)" && erk implement -d

Checkout plan #<plan_number>:
  Here:       erk br co --for-plan <plan_number>
  In new wt:  erk br co --new-slot --for-plan <plan_number>

Dispatch to queue: erk pr dispatch <plan_number>
```

### Next steps block (lines 207–220)

Update the "OR exit Claude Code first" fallback to match (trunk-unaware simplified version, no slot options):

```
Next steps:

View PR: <plan_url>

In Claude Code:
  Dispatch to queue: /erk:pr-dispatch — Dispatch plan for remote agent implementation

OR exit Claude Code first, then run one of:
  Checkout plan #<plan_number>:  erk br co --for-plan <plan_number>
  Dispatch to queue:             erk pr dispatch <plan_number>
```

## Verification

Run `/erk:plan-save` on a plan and confirm:
- Output shows "Implement plan #N:" section before "Checkout plan #N:" section
- Both `Here` and `In new wt` variants appear under Implement
- Each Implement variant has a `(dangerously):` sub-variant with `-d`
- No `--dangerous` flag appears in the non-dangerously variants
- No "Same slot" / "New slot" / "Local:" labels appear anywhere
- Ordering of Here vs In new wt matches trunk detection (on trunk → In new wt first)
