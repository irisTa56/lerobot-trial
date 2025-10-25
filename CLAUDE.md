# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a LeRobot experimentation playground using Dora-RS for dataflow orchestration and Gym-HIL for simulated robotics environments. The project enables keyboard-controlled robot simulation using a Panda arm in a pick-and-place task, without requiring real hardware.

## Development Commands

### Setup

```shell
# Install tools managed by mise
mise install

# Create virtual environment
uv venv -p "$(mise which python)"

# Install dependencies
uv sync --frozen

# Activate virtual environment
source .venv/bin/activate
```

### Code Quality

Run all checks:

```shell
mise all-checks
```

Individual checks:

```shell
mise format-py        # Format Python with ruff
mise lint-py          # Lint Python with ruff (runs format first)
mise type-check       # Type check with mypy
mise format-md        # Format markdown with rumdl
mise link-check       # Validate links with lychee
```

### Running the Simulation

The project uses Dora-RS dataflows defined in `dataflow-demo.yaml`. Start the simulation with:

```shell
dora up
dora start dataflow-demo.yaml
```

On macOS with MuJoCo, the `with_mujoco_on_mac.sh` wrapper script is required to set up the proper `DYLD_LIBRARY_PATH` for the Python shared library.

## Architecture

### Dora-RS Dataflow System

The system uses a dataflow architecture with two main nodes communicating via Apache Arrow messages:

1. **keyboard node** (`src/nodes/run_keyboard.py`):
   - Listens to keyboard input via pynput
   - Translates keystrokes into delta actions
   - Publishes action messages on the `action` channel
   - Runs asynchronously with keyboard events in a separate thread

2. **gym-hil node** (`src/nodes/run_gym_hil.py`):
   - Manages the Gym-HIL simulation environment (PandaPickCubeGymEnv)
   - Receives actions from keyboard node
   - Steps the environment at 10 Hz (100ms tick interval)
   - Handles episode termination/truncation

### Key Components

- **`lerobot_trial/config.py`**: Shared configuration, particularly `control_dt` (0.1s) which must match the Dora timer interval
- **`lerobot_trial/dora_ch.py`**: Utilities for Dora channel communication using PyArrow
- **`lerobot_trial/gym_hil.py`**: Environment setup and action conversion utilities

### Action Space

The action dictionary uses 4 dimensions (see `ActionDim` enum):

- `x`, `y`, `z`: Cartesian position deltas
- `gripper`: Gripper open/close state

Actions are converted to 7D environment arrays in `action_to_env_array()`:
`[x, y, z, 0, 0, 0, gripper]` (no orientation control)

### Keyboard Control Mapping

- Arrow keys: X/Y movement
- Left/Right Shift: Z movement (up/down)
- Left/Right Command: Gripper control

## Important Constraints

- `control_dt` in `config.py` MUST match the tick interval in `dataflow-demo.yaml`
- The keyboard node uses thread locking when accessing the Dora node due to concurrent keyboard events
- Type checking is strict (`mypy --strict`)
- Ruff enforces import sorting (extend-select = ["I"])
