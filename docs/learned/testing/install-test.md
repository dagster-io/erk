---
title: "Install-Test Guide"
read_when:
  - "testing erk installation"
  - "testing upgrade scenarios"
  - "adding install-test fixtures"
  - "debugging installation issues"
  - "erk-dev install-test"
---

# Install-Test Guide

Docker-based testing for erk installation and upgrade scenarios.

**Full documentation**: [dev/install-test/README.md](../../../dev/install-test/README.md)

## Quick Reference

```bash
# Build image (one-time)
erk-dev install-test build

# Fresh install test
erk-dev install-test fresh

# Interactive shell
erk-dev install-test shell

# Test with repo fixture
erk-dev install-test repo dagster-compass
```

## When to Use

- Testing fresh erk installation on repos with existing `.erk/` config
- Testing upgrade paths from older versions
- Validating repo-specific configurations

See the [full README](../../../dev/install-test/README.md) for detailed workflows and fixture management.
