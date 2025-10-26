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

Currently, FFmpeg's major version must be at most 7 to be compatible with PyTorch used by LeRobot:

```shell
brew install ffmpeg@7
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

The project uses Dora-RS dataflows. For teleoperation demo, use `dataflow-demo.yaml`:

```shell
dora up
dora start dataflow-demo.yaml
```

For recording datasets with LeRobot integration, use `dataflow-record.yaml`:

```shell
# Optional: clear previous records to record from scratch
rm -rf outputs/record/gym_hil_trial

# Run the dataflow to record dataset
dora run dataflow-record.yaml

# Visualize recorded dataset using Rerun
DYLD_LIBRARY_PATH="$(brew --prefix ffmpeg@7)/lib" lerobot-dataset-viz \
  --repo-id "example/gym_hil_trial" \
  --root "outputs/record/gym_hil_trial" \
  --episode-index 0
```

On macOS with MuJoCo, the `with_mujoco_on_mac.sh` wrapper script is required to set up the proper `DYLD_LIBRARY_PATH` for the Python shared library.

## Architecture

### Dora-RS Dataflow System

The system uses a tick-based dataflow architecture with multiple nodes communicating via Apache Arrow messages:

1. **keyboard node** ([run_keyboard.py](src/nodes/run_keyboard.py)):
   - Receives 10 Hz timer ticks from Dora
   - Listens to keyboard input via pynput in a separate thread
   - Maintains key press state for continuous movement
   - On each tick, publishes accumulated absolute position commands on the `action` channel
   - Publishes control commands (ESC, CTRL, SPACE) on the `control` channel for recording workflow
   - Uses thread locking when accessing the Dora node due to concurrent keyboard events

2. **gym-hil node** ([run_gym_hil.py](src/nodes/run_gym_hil.py)):
   - Manages the Gym-HIL simulation environment with absolute position control wrapper
   - Receives actions from keyboard node at 10 Hz
   - Steps the environment immediately upon receiving each action in BEFORE_DONE state
   - Publishes step input/output pairs (action at t, observation at t+1) on the `episode` channel using `step_io_to_message()`
   - Uses a state machine with three states: BEFORE_DONE, AFTER_DONE, RESETTING
   - Handles control commands: ESC to exit, SPACE to transition between states (finish episode → reset environment)

3. **lerobot node** ([record_by_lerobot.py](src/nodes/record_by_lerobot.py)) (recording mode only):
   - Receives step input/output pairs from gym-hil node and records them using LeRobot's recording infrastructure
   - Uses `GymClient.get_observation(synchronized=True)` during teleoperation to retrieve temporally aligned observations (observation at time t, synchronized with action at time t)
   - Handles control commands to manage recording workflow (start, stop, break episode)
   - Manages episode completion and environment reset coordination

### Key Components

- **[config.py](src/lerobot_trial/config.py)**: Shared configuration, particularly `control_dt` (0.1s) which must match the Dora timer interval
- **[dora_ch.py](src/lerobot_trial/dora_ch.py)**: Utilities for Dora channel communication using PyArrow, including `ChannelId` enum (ACTION, CONTROL, EPISODE) and `ControlCmd` int enum (ESC=1, CTRL=2, SPACE=3)
- **[gym_hil.py](src/lerobot_trial/gym_hil.py)**: Environment setup, action conversion utilities, and the `AbsolutePositionControl` wrapper that converts absolute position commands to delta actions by tracking the mocap position
- **[gym_client.py](src/lerobot_trial/gym_client.py)**: Dora event stream client for consuming gym-hil outputs. Tracks temporal alignment of actions and observations: action at time t, observation at time t (synchronized with action), and observation at time t+1 (result of applying action). Provides `get_observation(synchronized=True/False)` to choose between temporally aligned observations.
- **[gym_utils.py](src/lerobot_trial/gym_utils.py)**: Utilities for converting step input/output pairs (action at t, observation at t+1) to/from Dora messages using `step_io_to_message()` and `step_io_from_event()`
- **[lerobot_control_events.py](src/lerobot_trial/lerobot_control_events.py)**: Control event handling for LeRobot recording workflow
- **[hw_impl/](src/lerobot_trial/hw_impl/)**: Hardware implementation interfaces including:
  - **[base_robot.py](src/lerobot_trial/hw_impl/base_robot.py)**: `BaseRobot` accepts `with_teleop` parameter to control observation synchronization (synchronized observations for teleoperation, latest observations for policy execution)
  - **[gym_hil_recorder.py](src/lerobot_trial/hw_impl/gym_hil_recorder.py)**: `GymHILRecorderRobot` (uses `with_teleop=True`) and `GymHILRecorderTeleop` implementations for LeRobot recording

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

**Movement keys** (can be held down for continuous movement):

- Arrow keys: X/Y movement (continuous while held)
- Left/Right Shift: Z movement up/down (continuous while held)
- Left/Right Command: Gripper control (open/close while held)

**Control keys** (for recording workflow):

- **Esc**: Stop data recording and exit
- **Ctrl**: Transition to resetting phase (used to break and re-record an episode)
- **Space**: Finish the current episode or reset the environment (transitions through state machine)

Note: Control key bindings differ from the original LeRobot keyboard controls to avoid conflicts.

### Recording Workflow

When using [dataflow-record.yaml](dataflow-record.yaml) for dataset recording:

1. Execute `dora run dataflow-record.yaml`
2. Perform teleoperation to complete the task (e.g., pick up a cube)
3. The robot will freeze when the task is completed (gym-hil enters AFTER_DONE state)
4. Press **Space** to finish the episode (gym-hil enters RESETTING state)
5. LeRobot enters a resetting phase, which is not recorded
6. Press **Space** to reset the environment and finish the resetting phase (gym-hil returns to BEFORE_DONE state)
7. Repeat from step 2 until the desired number of episodes is recorded

Note: Between steps 3 and 4, the last received frame is recorded repeatedly.

The control commands enable flexible recording workflow:

- Use **Ctrl** to transition to resetting phase and re-record an episode if a mistake is made
- Use **Esc** to stop recording and exit when done

## Important Constraints

- `control_dt` in [config.py](src/lerobot_trial/config.py) MUST match the tick interval in [dataflow-demo.yaml](dataflow-demo.yaml) and [dataflow-record.yaml](dataflow-record.yaml) (all 100ms)
- The keyboard node receives tick events at 10 Hz and publishes actions on each tick
- The gym-hil node steps the environment immediately upon receiving each action only in BEFORE_DONE state
- The gym-hil node uses a state machine (BEFORE_DONE → AFTER_DONE → RESETTING → BEFORE_DONE) to manage episode lifecycle
- In recording mode, gym-hil publishes step input/output pairs (action at t, observation at t+1) after each step
- GymClient maintains temporal alignment: `_last_action` (action at t), `_last_observation` (observation at t), `_updated_observation` (observation at t+1)
- During teleoperation, use `get_observation(synchronized=True)` to get observation at time t; for policy execution, use `get_observation(synchronized=False)` to get the latest observation at time t+1
- The keyboard node uses thread locking when accessing the Dora node due to concurrent keyboard events
- Control commands (ESC, CTRL, SPACE) reset the action state to prevent unintended movement after control operations
- `ControlCmd` is an int enum (not str) with values: ESC=1, CTRL=2, SPACE=3
- Type checking is strict (`mypy --strict`)
- Ruff enforces import sorting (extend-select = ["I"])
