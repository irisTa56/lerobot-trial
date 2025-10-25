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

The system uses a tick-based dataflow architecture with two main nodes communicating via Apache Arrow messages:

1. **keyboard node** (`src/nodes/run_keyboard.py`):
   - Receives 10 Hz timer ticks from Dora
   - Listens to keyboard input via pynput in a separate thread
   - Maintains key press state for continuous movement
   - On each tick, publishes accumulated absolute position commands on the `action` channel
   - Uses thread locking when accessing the Dora node due to concurrent keyboard events

2. **gym-hil node** (`src/nodes/run_gym_hil.py`):
   - Manages the Gym-HIL simulation environment with absolute position control wrapper
   - Receives actions from keyboard node at 10 Hz
   - Steps the environment immediately upon receiving each action
   - Handles episode termination/truncation

### Key Components

- **`lerobot_trial/config.py`**: Shared configuration, particularly `control_dt` (0.1s) which must match the Dora timer interval
- **`lerobot_trial/dora_ch.py`**: Utilities for Dora channel communication using PyArrow
- **`lerobot_trial/gym_hil.py`**: Environment setup, action conversion utilities, and the `AbsolutePositionControl` wrapper that converts absolute position commands to delta actions by tracking the mocap position

### Action Space and Control

The action dictionary uses 4 dimensions (see `ActionDim` enum):

- `x`, `y`, `z`: Absolute Cartesian positions (accumulated from key presses at 0.005 units per tick)
- `gripper`: Gripper state (1.0 for open, -1.0 for close, 0.0 for neutral)

The `AbsolutePositionControl` wrapper in [gym_hil.py](src/lerobot_trial/gym_hil.py) converts these absolute positions to delta actions by:

1. Storing the initial position on reset as the origin
2. On each step, calculating the delta from the current position to the target position
3. Passing the delta action to the underlying environment

Actions are converted to 7D environment arrays in `action_to_env_array()`:
`[x, y, z, 0, 0, 0, gripper]` (no orientation control)

### Keyboard Control Mapping

Keys can be held down for continuous movement:

- Arrow keys: X/Y movement (continuous while held)
- Left/Right Shift: Z movement up/down (continuous while held)
- Left/Right Command: Gripper control (open/close while held)

## Important Constraints

- `control_dt` in [config.py](src/lerobot_trial/config.py) MUST match the tick interval in [dataflow-demo.yaml](dataflow-demo.yaml) (both 100ms)
- The keyboard node receives tick events at 10 Hz and publishes actions on each tick
- The gym-hil node steps the environment immediately upon receiving each action (no separate timer)
- The keyboard node uses thread locking when accessing the Dora node due to concurrent keyboard events
- Type checking is strict (`mypy --strict`)
- Ruff enforces import sorting (extend-select = ["I"])
