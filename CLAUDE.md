# Coding Guidelines for Claude

This document provides guidelines for AI assistants working on this codebase.

## Project Overview

This is a playground project to experiment with LeRobot without real robots.
The codebase is hybrid Python/Rust:

- **Python**: Main application code using LeRobot, FastAPI, Rerun, and Dora
- **Rust**: Native bindings for performance-critical components (in [rust/](rust/))
- **Build system**: Uses `maturin` to build Rust extensions and integrate with Python

Key directories:

- [lerobot/](lerobot/) - LeRobot submodule (excluded from most checks)
- [src/](src/) - Python package source
- [rust/src/](rust/src/) - Rust source code
- [scripts/](scripts/) - Utility scripts
- [tests/](tests/) - Test files

## Code Philosophy

- Write simple, human-readable code without unnecessary verbosity
- Avoid over-engineering and premature abstractions
- Excessive documentation is a maintenance burden - write self-explanatory code instead
- Only add comments where logic is not self-evident
- Keep solutions focused on the current requirements, not hypothetical future needs

## Code Structure and Organization

### Function and Method Ordering

Order code by abstraction level: constructors first, then public methods, then private helpers.
This lets readers understand the high-level purpose before diving into implementation details.

Place tightly coupled helpers immediately after their sole caller to keep related logic together.

## Development Workflow

### Pre-commit Checks

Before committing changes, run all checks:

```shell
mise pre-commit
```

This runs markdown formatting, link validation, Python checks (formatting, linting, type checking, tests), and Rust checks (formatting, linting, tests).

Individual checks can be run with `mise run <task>` (e.g., `mise run format-py`, `mise run lint-rs`).

### Language-Specific Guidelines

#### Python

Tools configured in [pyproject.toml](pyproject.toml):

- **Formatter**: `ruff format`
- **Linter**: `ruff check` with strict rules
- **Type checker**: `mypy` with strict mode
- **Test runner**: `pytest`

The `lerobot/` directory is excluded from all checks as it's a submodule.

#### Rust

- **Formatter**: `cargo fmt`
- **Linter**: `cargo clippy` with warnings denied
- **Test runner**: `cargo test`

All Rust commands run in the [rust/](rust/) directory.

### Python/Rust Integration

When modifying Rust code exposed to Python:

1. Update Rust implementation in [rust/src/](rust/src/)
2. Update type stubs in [src/lerobot_trial/_rust.pyi](src/lerobot_trial/_rust.pyi)
3. Run `mise pre-commit` to ensure both Python and Rust tests pass

The type stub file provides IDE autocompletion and type checking for the Rust-implemented Python module.

## Maintenance

Update this document proactively when discovering new patterns, conventions, or guidelines that would benefit future development.
