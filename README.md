# LeRobot Trial

Playground to experiment with LeRobot without real robots.

## Setup

Ensure the *latest* [`mise`](https://mise.jdx.dev/getting-started.html) is installed, then run:

```shell
# Install tools managed by mise
mise install

# Create virtual environment
uv venv -p "$(mise which python)"

# Install Python dependencies
uv sync --frozen
# If Git LFS smudge error occurs, run:
# GIT_LFS_SKIP_SMUDGE=1 uv sync --frozen

# Activate virtual environment
source .venv/bin/activate
```

Currently, FFmpeg's major version must be at most 7 to be compatible with PyTorch used by LeRobot.

```shell
brew install ffmpeg@7
```

## Development

You can use [mise to set up pre-commit hooks](https://mise.jdx.dev/cli/generate/git-pre-commit.html) for this repository.

```shell
mise generate git-pre-commit --write --task=pre-commit
```

For all available tasks, see [`mise.toml`](mise.toml).
