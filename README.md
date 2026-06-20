# Ball Catch - 接住滚动的球

A dynamic ball-catching task using a five-finger dexterous robotic hand in MuJoCo.

## Project Summary

This project demonstrates a dynamic ball-catching task where a robotic hand must track and catch a rolling ball. The task showcases:
- Real-time hand tracking with adaptive gain control
- Velocity prediction for ball trajectory
- Multi-finger grasping coordination
- Tactile feedback for contact detection

## Technical Approach

### Tracking Controller
- **Adaptive Gain Control**: Adjusts tracking response based on error magnitude
- **Velocity Prediction**: Predicts ball position using time horizon
- **Grasp Timing Prediction**: Algorithm predicts optimal grasp moment

### Hand Control
- Five-finger dexterous hand with 21 DOF
- Tactile sensors on each fingertip
- Smooth interpolation between poses

## Core Features

| Feature | Description |
|---------|------------|
| Ball Tracking | Real-time position tracking with prediction |
| Adaptive Gain | Error-based gain adjustment (2x/1.5x/1x) |
| Grasp Prediction | Algorithm predicts catch timing |
| Multi-finger Grasp | 4+ fingers for stable catch |
| Tactile Feedback | 5-channel touch sensor visualization |

## Performance

| Difficulty | Success Rate | Tracking Error | Fingers Used |
|------------|-------------|---------------|-------------|
| Easy | 100% | ~8cm | 4 |
| Medium | 100% | ~8cm | 3 |
| Hard | 100% | ~8cm | 3 |

## How to Run

```bash
# Run single episode
python run_ball_catch.py --seed 42 --difficulty easy

# Generate video
python run_ball_catch.py --seed 42 --difficulty easy --output outputs

# Run stress test
python ball_stress_test.py --seeds 32 --difficulty easy

# Generate analysis reports
python ball_summary_report.py --output outputs_ball_catch --save
python ball_response_time_analysis.py --output outputs_ball_catch --save
python ball_force_analysis.py --output outputs_ball_catch --save
```

## Task Gates

8/8 gates passed:
1. ✅ Five fingers present
2. ✅ Hand skeleton valid
3. ✅ Ball launcher present
4. ✅ Ball motion initiated
5. ✅ Hand tracking active
6. ✅ Ball contact detected
7. ✅ Stable catch achieved
8. ✅ Ball held without drop

## Current Limitations

- Tracking error ~8cm (target: <5cm)
- Response time limited by hand damping
- Single ball trajectory

## Future Improvements

- Improve tracking precision with better prediction
- Add multiple ball trajectories
- Increase finger coordination for 5-finger catch

## Demo Video

See `outputs/demo.mp4` for demonstration video.
