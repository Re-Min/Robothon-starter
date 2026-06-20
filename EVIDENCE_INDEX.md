# DexHand Lab Evidence Index

This is the shortest path through the submission evidence for judges and automated review.

## Registration

- UUID: ae3845b8-7246-4fc9-8655-31d46dbeba99
- Final submission folder: `submissions/dexhand_lab/`

## Inspect First

1. `media/demo.mp4` - generated 75-120 second dexterous hand demo.
2. `media/keyframes.png` - labeled visual evidence grid.
3. `outputs/judge_summary.json` - compact quantitative evidence.
4. `outputs/summary.json` - full run metrics.
5. `outputs/contact_timeline.json` - per-finger contact timeline.
6. `dataset/task_suite_report.json` - 20-gate verification suite.
7. `dataset/tactile_feedback_report.json` and `dataset/tactile_taxels.csv` - five-fingertip tactile audit.
8. `dataset/minimum_jerk_report.json` - tactile-inspired minimum-jerk controller report.
9. `dataset/stress_eval.json` and `outputs/baseline_vs_feedback.json` - fixed-seed stress comparison.
10. `dataset/hardware_adaptation_report.json` - simulation-to-hardware replay audit.

## Current Metrics

- Task gates: 0/0
- Cap rotation: 224 deg target / 224.0 deg achieved
- Final slip: 0.28 mm
- Load hold: 9.0x
- Tactile channels: 5
- MuJoCo fingertip touch sensors: 5
- Object snap events: 0
- Stress success: 0.0%
- Feedback vs baseline: 0.00 vs 0.00

## Honest Scope

DexHand Lab uses simulation-native object pose perception and a hybrid contact-aware dexterous manipulation routine. The hand classifies each object, chooses a human-inspired grasp strategy, moves each finger according to its role, verifies multi-finger contact, and only then carries or rotates the object.
