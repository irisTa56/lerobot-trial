# LeRobot Trial

Playground to experiment with LeRobot without real robots.

## Setup

Ensure the *latest* [`mise`](https://mise.jdx.dev) is installed, then run:

```shell
# Install tools managed by mise
mise install

# Create virtual environment
uv venv -p "$(mise which python)"

# Install Python dependencies
uv sync --frozen

# Activate virtual environment
source .venv/bin/activate
```

## Development

For code quality checks, run `mise all-checks`.
Refer to `mise.toml` for details.
