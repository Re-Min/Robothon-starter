# DexHand Lab Hardware Adaptation Audit

This file documents a simulation-to-hardware replay audit. It is not a physical robot trial.

The command stream maps the simulated five-finger hand joints to LEAP/Shadow-style joint channels, clamps ranges, limits pressure targets, and includes emergency-stop checks for excessive slip or pressure.

---

## Ball Catch Task - Hardware Adaptation

### Overview

The Ball Catch task requires a dexterous five-finger hand to track and catch a rolling ball. This document maps the simulation components to potential hardware implementations.

### Robot Platform Mapping

#### Simulated → Hardware Joint Mapping

| Simulated Joint | Hardware Equivalent | Control Signal | Unit |
|----------------|-------------------|----------------|------|
| `hand_x` | Base X-axis linear slide | Position command | m |
| `hand_y` | Base Y-axis linear slide | Position command | m |
| `hand_z` | Base Z-axis linear slide | Position command | m |
| `wrist_yaw` | Wrist rotation (yaw) | Position command | rad |
| `wrist_pitch` | Wrist rotation (pitch) | Position command | rad |
| `wrist_roll` | Wrist rotation (roll) | Position command | rad |
| `thumb_cmc_opposition` | Thumb CMC opposition | Position command | rad |
| `thumb_mcp_flexion` | Thumb MCP flexion | Position command | rad |
| `thumb_ip_flexion` | Thumb IP flexion | Position command | rad |
| `index_mcp_flexion` | Index MCP flexion | Position command | rad |
| `index_pip_flexion` | Index PIP flexion | Position command | rad |
| `index_dip_flexion` | Index DIP flexion | Position command | rad |
| `middle_*` | Middle finger joints (4 DOF) | Position command | rad |
| `ring_*` | Ring finger joints (4 DOF) | Position command | rad |
| `little_*` | Little finger joints (4 DOF) | Position command | rad |

**Total DOF: 21 (3 linear + 3 wrist + 5 fingers × 3 joints)**

### Control Parameters

#### Position Control Gains

```python
# Joint position control gains
HAND_SLIDE_KP = 160      # Linear slide proportional gain
WRIST_KP = 80             # Wrist rotation proportional gain  
FINGER_KP = 65            # Finger joint proportional gain

# Control frequency
CONTROL_FREQUENCY_HZ = 50  # 50 Hz real-time control
CONTROL_PERIOD_S = 0.02    # 20ms control period
```

#### Joint Limits

```python
# Linear slides (m)
HAND_X_RANGE = (-0.40, 0.40)
HAND_Y_RANGE = (-0.22, 0.34)
HAND_Z_RANGE = (-0.13, 0.06)

# Wrist rotations (rad)
WRIST_YAW_RANGE = (-0.61, 0.61)    # ±35°
WRIST_PITCH_RANGE = (-0.44, 0.44)   # ±25°
WRIST_ROLL_RANGE = (-0.44, 0.44)    # ±25°
```

### Tactile Sensor Mapping

#### Fingertip Sensors (5 channels)

| Finger | Sensor Channel | Data Type | Range |
|--------|---------------|-----------|-------|
| Thumb | `touch_thumb_tip` | Force | 0-10 N |
| Index | `touch_index_tip` | Force | 0-10 N |
| Middle | `touch_middle_tip` | Force | 0-10 N |
| Ring | `touch_ring_tip` | Force | 0-10 N |
| Little | `touch_little_tip` | Force | 0-10 N |

#### Contact Detection

```python
# Contact detection threshold
CONTACT_THRESHOLD = 0.5  # Newtons

# Stable grasp requirement
STABLE_GRASP_MIN_FINGERS = 2  # Minimum fingers for stable catch
```

### Ball Tracking System

#### Vision System Interface

```python
# Ball position from vision system
BALL_POSITION_TOPIC = "/ball_tracker/position"  # [x, y, z] in meters
BALL_VELOCITY_TOPIC = "/ball_tracker/velocity" # [vx, vy, vz] in m/s

# Tracking parameters
TRACKING_FREQUENCY_HZ = 30   # Vision system update rate
POSITION_LATENCY_MS = 50     # Typical vision latency
```

#### Tracking Controller Algorithm

```python
# Prediction-based tracking (from ball_tracker.py)
PREDICTION_TIME_S = 0.15     # 150ms lookahead
TRACKING_GAIN = 8.0          # Position error gain
MAX_ADJUSTMENT_M = 0.08      # Maximum hand adjustment per cycle

# Error calculation
ball_pos = get_ball_position()
ball_vel = get_ball_velocity()
speed = norm(ball_vel[:2])

if speed > 0.01:
    # 70% current position + 30% predicted position
    lead_x = ball_vel[0] * PREDICTION_TIME_S
    lead_y = ball_vel[1] * PREDICTION_TIME_S
    error_x = error_x * 0.7 + lead_x * 0.3
    error_y = error_y * 0.7 + lead_y * 0.3
```

### Command Stream Format

```python
# 50Hz command stream structure
class HandCommand:
    timestamp: float          # seconds
    hand_x: float            # meters
    hand_y: float            # meters  
    hand_z: float            # meters
    wrist_yaw: float         # radians
    wrist_pitch: float       # radians
    wrist_roll: float        # radians
    finger_targets: dict      # {joint_name: position}
    emergency_stop: bool      # safety flag
```

### Safety Limits

```python
# Joint velocity limits
MAX_HAND_VELOCITY = 0.5      # m/s for linear slides
MAX_WRIST_VELOCITY = 1.0    # rad/s for wrist
MAX_FINGER_VELOCITY = 2.0   # rad/s for fingers

# Ball approach zones
APPROACH_ZONE_RADIUS = 0.15  # meters
GRASP_ZONE_RADIUS = 0.08     # meters

# Table boundaries
TABLE_BOUND_X = 0.50         # meters
TABLE_BOUND_Y = 0.40         # meters
```

### Calibration Procedure

1. **Joint Calibration**
   - Home position verification
   - Joint limit validation
   - Zero offset calibration

2. **Tactile Sensor Calibration**
   - Zero reading with no contact
   - Load cell calibration with known forces
   - Threshold setting for contact detection

3. **Vision System Calibration**
   - Camera intrinsic parameters
   - World coordinate mapping
   - Ball tracking accuracy verification

### Deployment Checklist

- [ ] Joint limits verified
- [ ] Tactile sensors calibrated
- [ ] Vision system operational
- [ ] Control loop stable at 50 Hz
- [ ] Safety limits enabled
- [ ] Emergency stop functional
- [ ] Ball launcher synchronized
- [ ] Human observers for initial tests

### Known Limitations

1. **Control Latency**: Real hardware has ~50ms latency vs <1ms in simulation
2. **Sensor Noise**: Tactile sensors require filtering
3. **Mechanical Backlash**: Joints may have unmodeled backlash
4. **Vision Latency**: Ball tracking has inherent delay

### Future Improvements

1. Adaptive gain scheduling based on tracking error
2. Learning-based grasp prediction
3. Force feedback control for grasp stability
4. Real-time trajectory optimization
