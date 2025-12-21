# Coding Guidelines for Claude

This document provides guidelines for AI assistants working on this codebase.

## Project Overview

This is a playground project to experiment with LeRobot without real robots. The codebase is hybrid Python/Rust:

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

## Development Workflow

### Pre-commit Checks

Before committing changes, ensure all pre-commit checks pass:

```shell
mise pre-commit
```

This runs all checks defined in [mise.toml](mise.toml):

- Markdown formatting (`format-md`)
- Link validation (`link-check`)
- Python formatting, linting, type checking, and tests (`pre-commit-py`)
- Rust formatting, linting, and tests (`pre-commit-rs`)

### Language-Specific Guidelines

#### Python

Tools configured in [pyproject.toml](pyproject.toml):

- **Formatter**: `ruff format`
- **Linter**: `ruff check` with strict rules (see `[tool.ruff.lint]`)
- **Type checker**: `mypy` with strict mode enabled
- **Test runner**: `pytest`

The `lerobot/` directory is excluded from all checks as it's a submodule.

#### Rust

Standard Rust toolchain:

- **Formatter**: `cargo fmt`
- **Linter**: `cargo clippy` with warnings denied (`-D warnings`)
- **Test runner**: `cargo test`

All Rust commands run in the [rust/](rust/) directory.

### Running Individual Checks

You can run specific checks using `mise` tasks:

```shell
# Python
mise run format-py      # Format Python code
mise run lint-py        # Lint Python code
mise run typecheck      # Type check with mypy
mise run test-py        # Run Python tests

# Rust
mise run format-rs      # Format Rust code
mise run lint-rs        # Lint Rust code with clippy
mise run test-rs        # Run Rust tests

# Other
mise run format-md      # Format markdown files
mise run link-check     # Check for broken links
```

## Maintenance

Update this document proactively when discovering new patterns, conventions, or guidelines that would benefit future development.
