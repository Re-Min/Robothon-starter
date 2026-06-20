"""
ball_tracker.py - 接球任务的手球追踪控制器

这个模块提供滚球追踪的核心控制逻辑，包括：
- 球的发射控制
- 实时位置/速度获取
- 轨迹预测
- 手部追踪控制
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np


# 难度配置 - 优化追踪策略
TRACKING_CONFIGS = {
    "easy": {
        "description": "极慢速滚动，手提前预测位置",
        "launch_velocity": (0.06, 0.02, 0.0),  # m/s (vx, vy, vz)
        "tracking_gain": 11.0,  # 适度追踪增益
        "max_adjustment": 0.100,  # 调整量
        "grasp_threshold": 0.12,  # 抓取阈值
        "time_horizon": 0.5,  # 预测时间
        "catch_position": (-0.30, -0.04),  # 接球准备位置
    },
    "medium": {
        "description": "慢速滚动，预测追踪",
        "launch_velocity": (0.08, 0.03, 0.0),  # m/s
        "tracking_gain": 10.0,  # 适度追踪增益
        "max_adjustment": 0.100,  # m
        "grasp_threshold": 0.10,  # m
        "time_horizon": 0.4,  # s
        "catch_position": (-0.28, -0.04),  # 接球准备位置
    },
    "hard": {
        "description": "中速滚动，快速反应",
        "launch_velocity": (0.10, 0.04, 0.0),  # m/s
        "tracking_gain": 9.0,
        "max_adjustment": 0.090,  # m
        "grasp_threshold": 0.08,  # m
        "time_horizon": 0.3,  # s
        "catch_position": (-0.26, -0.04),  # 接球准备位置
    },
}


# 抓取配置 - 关节角度目标
GRASP_CONFIG = {
    "open_wait": {  # 张开手等待 - 更展开以便接球
        "thumb_cmc_opposition": 0.35,  # 适度对掌
        "thumb_cmc_abduction": 0.65,  # 适度外展
        "thumb_mcp_flexion": 0.08,
        "thumb_ip_flexion": 0.04,
        "index_mcp_abduction": -0.22,  # 适度外展
        "index_mcp_flexion": 0.08,
        "index_pip_flexion": 0.04,
        "index_dip_flexion": 0.02,
        "middle_mcp_abduction": -0.04,
        "middle_mcp_flexion": 0.06,
        "middle_pip_flexion": 0.03,
        "middle_dip_flexion": 0.02,
        "ring_mcp_abduction": 0.12,
        "ring_mcp_flexion": 0.08,
        "ring_pip_flexion": 0.04,
        "ring_dip_flexion": 0.02,
        "little_mcp_abduction": 0.22,
        "little_mcp_flexion": 0.08,
        "little_pip_flexion": 0.04,
        "little_dip_flexion": 0.02,
    },
    "close_grasp": {  # 闭合抓取 - 完全包裹球
        "thumb_cmc_opposition": 1.25,  # 适度对掌
        "thumb_cmc_abduction": 0.55,  # 适度外展
        "thumb_mcp_flexion": 0.95,  # 完全弯曲
        "thumb_ip_flexion": 0.75,  # 完全弯曲
        "index_mcp_abduction": -0.15,
        "index_mcp_flexion": 1.12,  # 弯曲
        "index_pip_flexion": 1.22,
        "index_dip_flexion": 0.82,
        "middle_mcp_abduction": -0.03,
        "middle_mcp_flexion": 1.16,  # 弯曲
        "middle_pip_flexion": 1.26,
        "middle_dip_flexion": 0.86,
        "ring_mcp_abduction": 0.06,
        "ring_mcp_flexion": 1.14,
        "ring_pip_flexion": 1.24,
        "ring_dip_flexion": 0.84,
        "little_mcp_abduction": 0.15,
        "little_mcp_flexion": 1.08,
        "little_pip_flexion": 1.18,
        "little_dip_flexion": 0.78,
    },
    "hold_stable": {  # 保持稳定
        "thumb_cmc_opposition": 0.95,
        "thumb_cmc_abduction": 0.42,
        "thumb_mcp_flexion": 0.70,
        "thumb_ip_flexion": 0.44,
        "index_mcp_abduction": -0.14,
        "index_mcp_flexion": 0.82,
        "index_pip_flexion": 0.80,
        "index_dip_flexion": 0.48,
        "middle_mcp_abduction": -0.02,
        "middle_mcp_flexion": 0.90,
        "middle_pip_flexion": 0.84,
        "middle_dip_flexion": 0.50,
        "ring_mcp_abduction": 0.06,
        "ring_mcp_flexion": 0.96,
        "ring_pip_flexion": 0.88,
        "ring_dip_flexion": 0.56,
        "little_mcp_abduction": 0.12,
        "little_mcp_flexion": 0.92,
        "little_pip_flexion": 0.84,
        "little_dip_flexion": 0.54,
    },
}


# 手部展示姿态
HAND_DISPLAY_POSES = [
    {  # 0: 完全张开
        "thumb_cmc_opposition": 0.18,
        "thumb_cmc_abduction": 0.22,
        "thumb_mcp_flexion": 0.08,
        "thumb_ip_flexion": 0.04,
        "index_mcp_abduction": -0.08,
        "index_mcp_flexion": 0.04,
        "index_pip_flexion": 0.03,
        "index_dip_flexion": 0.02,
        "middle_mcp_abduction": 0.00,
        "middle_mcp_flexion": 0.04,
        "middle_pip_flexion": 0.03,
        "middle_dip_flexion": 0.02,
        "ring_mcp_abduction": 0.05,
        "ring_mcp_flexion": 0.04,
        "ring_pip_flexion": 0.03,
        "ring_dip_flexion": 0.02,
        "little_mcp_abduction": 0.11,
        "little_mcp_flexion": 0.04,
        "little_pip_flexion": 0.03,
        "little_dip_flexion": 0.02,
    },
    {  # 1: 拇指对掌
        "thumb_cmc_opposition": 0.80,
        "thumb_cmc_abduction": 0.50,
        "thumb_mcp_flexion": 0.50,
        "thumb_ip_flexion": 0.30,
        "index_mcp_abduction": -0.08,
        "index_mcp_flexion": 0.04,
        "index_pip_flexion": 0.03,
        "index_dip_flexion": 0.02,
        "middle_mcp_abduction": 0.00,
        "middle_mcp_flexion": 0.04,
        "middle_pip_flexion": 0.03,
        "middle_dip_flexion": 0.02,
        "ring_mcp_abduction": 0.05,
        "ring_mcp_flexion": 0.04,
        "ring_pip_flexion": 0.03,
        "ring_dip_flexion": 0.02,
        "little_mcp_abduction": 0.11,
        "little_mcp_flexion": 0.04,
        "little_pip_flexion": 0.03,
        "little_dip_flexion": 0.02,
    },
    {  # 2: 食指弯曲
        "thumb_cmc_opposition": 0.18,
        "thumb_cmc_abduction": 0.22,
        "thumb_mcp_flexion": 0.08,
        "thumb_ip_flexion": 0.04,
        "index_mcp_abduction": -0.08,
        "index_mcp_flexion": 0.70,
        "index_pip_flexion": 0.65,
        "index_dip_flexion": 0.40,
        "middle_mcp_abduction": 0.00,
        "middle_mcp_flexion": 0.04,
        "middle_pip_flexion": 0.03,
        "middle_dip_flexion": 0.02,
        "ring_mcp_abduction": 0.05,
        "ring_mcp_flexion": 0.04,
        "ring_pip_flexion": 0.03,
        "ring_dip_flexion": 0.02,
        "little_mcp_abduction": 0.11,
        "little_mcp_flexion": 0.04,
        "little_pip_flexion": 0.03,
        "little_dip_flexion": 0.02,
    },
    {  # 3: 握拳
        "thumb_cmc_opposition": 1.10,
        "thumb_cmc_abduction": 0.40,
        "thumb_mcp_flexion": 0.80,
        "thumb_ip_flexion": 0.60,
        "index_mcp_abduction": -0.10,
        "index_mcp_flexion": 1.00,
        "index_pip_flexion": 0.95,
        "index_dip_flexion": 0.60,
        "middle_mcp_abduction": -0.02,
        "middle_mcp_flexion": 1.00,
        "middle_pip_flexion": 0.95,
        "middle_dip_flexion": 0.60,
        "ring_mcp_abduction": 0.06,
        "ring_mcp_flexion": 1.00,
        "ring_pip_flexion": 0.95,
        "ring_dip_flexion": 0.60,
        "little_mcp_abduction": 0.12,
        "little_mcp_flexion": 1.00,
        "little_pip_flexion": 0.95,
        "little_dip_flexion": 0.60,
    },
    {  # 4: OK手势
        "thumb_cmc_opposition": 0.90,
        "thumb_cmc_abduction": 0.50,
        "thumb_mcp_flexion": 0.50,
        "thumb_ip_flexion": 0.80,  # 拇指指尖弯曲
        "index_mcp_abduction": -0.08,
        "index_mcp_flexion": 0.90,
        "index_pip_flexion": 0.85,
        "index_dip_flexion": 0.50,
        "middle_mcp_abduction": 0.00,
        "middle_mcp_flexion": 0.04,
        "middle_pip_flexion": 0.03,
        "middle_dip_flexion": 0.02,
        "ring_mcp_abduction": 0.05,
        "ring_mcp_flexion": 0.04,
        "ring_pip_flexion": 0.03,
        "ring_dip_flexion": 0.02,
        "little_mcp_abduction": 0.11,
        "little_mcp_flexion": 0.04,
        "little_pip_flexion": 0.03,
        "little_dip_flexion": 0.02,
    },
    {  # 5: 捏取手势
        "thumb_cmc_opposition": 0.75,
        "thumb_cmc_abduction": 0.40,
        "thumb_mcp_flexion": 0.40,
        "thumb_ip_flexion": 0.20,
        "index_mcp_abduction": -0.04,
        "index_mcp_flexion": 0.20,
        "index_pip_flexion": 0.10,
        "index_dip_flexion": 0.05,
        "middle_mcp_abduction": 0.00,
        "middle_mcp_flexion": 0.04,
        "middle_pip_flexion": 0.03,
        "middle_dip_flexion": 0.02,
        "ring_mcp_abduction": 0.05,
        "ring_mcp_flexion": 0.04,
        "ring_pip_flexion": 0.03,
        "ring_dip_flexion": 0.02,
        "little_mcp_abduction": 0.11,
        "little_mcp_flexion": 0.04,
        "little_pip_flexion": 0.03,
        "little_dip_flexion": 0.02,
    },
    {  # 6: 张开手指
        "thumb_cmc_opposition": 0.25,
        "thumb_cmc_abduction": 0.70,
        "thumb_mcp_flexion": 0.12,
        "thumb_ip_flexion": 0.06,
        "index_mcp_abduction": -0.18,
        "index_mcp_flexion": 0.06,
        "index_pip_flexion": 0.04,
        "index_dip_flexion": 0.02,
        "middle_mcp_abduction": 0.00,
        "middle_mcp_flexion": 0.06,
        "middle_pip_flexion": 0.04,
        "middle_dip_flexion": 0.02,
        "ring_mcp_abduction": 0.14,
        "ring_mcp_flexion": 0.06,
        "ring_pip_flexion": 0.04,
        "ring_dip_flexion": 0.02,
        "little_mcp_abduction": 0.22,
        "little_mcp_flexion": 0.06,
        "little_pip_flexion": 0.04,
        "little_dip_flexion": 0.02,
    },
    {  # 7: 收回
        "thumb_cmc_opposition": 0.60,
        "thumb_cmc_abduction": 0.30,
        "thumb_mcp_flexion": 0.40,
        "thumb_ip_flexion": 0.25,
        "index_mcp_abduction": -0.06,
        "index_mcp_flexion": 0.50,
        "index_pip_flexion": 0.45,
        "index_dip_flexion": 0.28,
        "middle_mcp_abduction": -0.02,
        "middle_mcp_flexion": 0.50,
        "middle_pip_flexion": 0.45,
        "middle_dip_flexion": 0.28,
        "ring_mcp_abduction": 0.04,
        "ring_mcp_flexion": 0.50,
        "ring_pip_flexion": 0.45,
        "ring_dip_flexion": 0.28,
        "little_mcp_abduction": 0.08,
        "little_mcp_flexion": 0.50,
        "little_pip_flexion": 0.45,
        "little_dip_flexion": 0.28,
    },
]


# 手指关节列表 (与scene.xml一致)
FINGER_JOINTS = (
    "thumb_cmc_opposition",
    "thumb_cmc_abduction",
    "thumb_mcp_flexion",
    "thumb_ip_flexion",
    "index_mcp_abduction",
    "index_mcp_flexion",
    "index_pip_flexion",
    "index_dip_flexion",
    "middle_mcp_abduction",
    "middle_mcp_flexion",
    "middle_pip_flexion",
    "middle_dip_flexion",
    "ring_mcp_abduction",
    "ring_mcp_flexion",
    "ring_pip_flexion",
    "ring_dip_flexion",
    "little_mcp_abduction",
    "little_mcp_flexion",
    "little_pip_flexion",
    "little_dip_flexion",
)


@dataclass
class TrackingStats:
    """追踪统计数据"""
    launch_time: float = 0.0
    first_contact_time: float | None = None
    catch_time: float | None = None
    tracking_error_sum: float = 0.0
    tracking_samples: int = 0
    max_tracking_error: float = 0.0


class BallTracker:
    """
    滚球追踪控制器

    负责：
    1. 球的发射（施加初速度）
    2. 实时获取球的位置和速度
    3. 预测球的轨迹
    4. 计算手部追踪调整量
    5. 评估抓取质量
    """

    # 手部滑动关节范围 (与scene.xml一致)
    HAND_X_RANGE = (-0.40, 0.40)
    HAND_Y_RANGE = (-0.22, 0.34)

    def __init__(
        self,
        model,
        data,
        ball_body_name: str = "sphere_object",
        palm_site_name: str = "palm_center_site",
    ):
        """
        初始化追踪器

        Args:
            model: MuJoCo模型
            data: MuJoCo数据
            ball_body_name: 球体body名称
            palm_site_name: 手掌site名称
        """
        import mujoco

        self._model = model
        self._data = data
        self._mujoco = mujoco

        # 获取body和site的ID
        self._ball_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, ball_body_name)
        if self._ball_id < 0:
            raise ValueError(f"Ball body '{ball_body_name}' not found in model")

        self._palm_site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, palm_site_name)
        if self._palm_site_id < 0:
            raise ValueError(f"Palm site '{palm_site_name}' not found in model")

        # 获取球体freejoint的地址
        ball_joint_name = ball_body_name + "_joint"
        self._ball_joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, ball_joint_name)
        if self._ball_joint_id < 0:
            raise ValueError(f"Ball joint '{ball_joint_name}' not found in model")

        self._ball_qpos_adr = int(model.jnt_qposadr[self._ball_joint_id])
        self._ball_qvel_adr = int(model.jnt_dofadr[self._ball_joint_id])

        # 追踪状态
        self.launched = False
        self.launch_time: float | None = None
        self.initial_velocity = np.zeros(3)
        self.ball_attached = False  # 球是否被抓住

        # 追踪参数 (会在configure时设置)
        self.tracking_gain = 2.5
        self.max_adjustment = 0.03
        self.grasp_threshold = 0.08
        self.time_horizon = 0.5

        # 统计数据
        self.stats = TrackingStats()

    def configure(self, difficulty: str) -> None:
        """
        配置追踪参数

        Args:
            difficulty: 难度级别 ("easy", "medium", "hard")
        """
        config = TRACKING_CONFIGS.get(difficulty, TRACKING_CONFIGS["medium"])
        self.tracking_gain = config["tracking_gain"]
        self.max_adjustment = config["max_adjustment"]
        self.grasp_threshold = config["grasp_threshold"]
        self.time_horizon = config["time_horizon"]

    def launch(self, velocity: tuple[float, float, float], seed: int | None = None) -> None:
        """
        发射球，施加初速度

        Args:
            velocity: 初速度 (vx, vy, vz) in m/s
            seed: 随机种子，用于生成确定性扰动
        """
        if self.launched:
            return  # 只能发射一次

        rng = np.random.default_rng(seed)

        # 添加微小随机扰动 (±5% 速度 + 微小随机)
        scale = 1.0 + rng.uniform(-0.05, 0.05)
        vx = velocity[0] * scale + rng.uniform(-0.003, 0.003)
        vy = velocity[1] * scale + rng.uniform(-0.003, 0.003)
        vz = velocity[2] + rng.uniform(-0.002, 0.002)

        self.initial_velocity = np.array([vx, vy, vz])

        # 设置球的速度 (qvel的前3个分量是线速度)
        self._data.qvel[self._ball_qvel_adr:self._ball_qvel_adr + 3] = [vx, vy, vz]

        self.launched = True
        self.launch_time = float(self._data.time)
        self.stats.launch_time = self.launch_time

    def reset(self) -> None:
        """重置追踪状态"""
        self.launched = False
        self.launch_time = None
        self.initial_velocity = np.zeros(3)
        self.ball_attached = False
        self.stats = TrackingStats()

    def get_ball_position(self) -> np.ndarray:
        """
        获取球当前世界坐标

        Returns:
            球的位置 [x, y, z]
        """
        return self._data.xpos[self._ball_id].copy()

    def get_ball_velocity(self) -> np.ndarray:
        """
        获取球当前速度

        Returns:
            球的速度 [vx, vy, vz]
        """
        return self._data.qvel[self._ball_qvel_adr:self._ball_qvel_adr + 3].copy()

    def get_palm_position(self) -> np.ndarray:
        """
        获取手掌中心的世界坐标

        Returns:
            手掌位置 [x, y, z]
        """
        return self._data.site_xpos[self._palm_site_id].copy()

    def predict_contact_time(
        self,
        hand_pos: np.ndarray,
        time_horizon: float | None = None,
    ) -> float:
        """
        预测球到达手部高度的预计时间

        Args:
            hand_pos: 手部位置
            time_horizon: 最大预测时间

        Returns:
            预计到达时间(秒)，如果速度太慢返回inf
        """
        if time_horizon is None:
            time_horizon = self.time_horizon

        pos = self.get_ball_position()
        vel = self.get_ball_velocity()

        # 2D平面距离
        pos_2d = pos[:2]
        vel_2d = vel[:2]

        speed_2d = np.linalg.norm(vel_2d)
        if speed_2d < 0.01:
            return float("inf")

        # 投影误差到速度方向
        error = hand_pos[:2] - pos_2d

        if speed_2d > 1e-6:
            proj_speed = np.dot(vel_2d / speed_2d, error)
            if proj_speed > 0:
                return float(proj_speed / speed_2d)

        return time_horizon

    def predict_grasp_timing(self, hand_pos: np.ndarray) -> dict:
        """
        预测最佳抓取时机

        综合分析：
        1. 球到达时间
        2. 手部响应时间
        3. 抓取质量预测
        4. 最佳闭合时机

        Args:
            hand_pos: 手部位置

        Returns:
            包含预测信息的字典
        """
        ball_pos = self.get_ball_position()
        ball_vel = self.get_ball_velocity()
        speed_2d = np.linalg.norm(ball_vel[:2])

        # 1. 计算球到手的距离
        distance = np.linalg.norm(ball_pos[:2] - hand_pos[:2])

        # 2. 预测球到达时间
        if speed_2d > 0.01:
            time_to_reach = distance / speed_2d
        else:
            time_to_reach = float("inf")

        # 3. 手部响应延迟（估算）
        # 考虑到控制延迟和机械惯性，预测手指完全闭合需要约0.3秒
        hand_response_time = 0.3

        # 4. 计算最佳手指闭合时机
        # 当time_to_reach ≈ hand_response_time时，手指应该开始闭合
        grasp_quality = self.get_grasp_quality(hand_pos)

        # 5. 预测抓取成功率
        # 考虑距离、速度、方向偏差
        velocity_alignment = 1.0
        if speed_2d > 0.01:
            # 计算速度方向是否朝向手部
            to_hand = hand_pos[:2] - ball_pos[:2]
            alignment = np.dot(to_hand, ball_vel[:2]) / (distance * speed_2d)
            velocity_alignment = max(0.0, alignment)

        # 综合评分
        quality_factor = grasp_quality
        distance_factor = max(0.0, 1.0 - distance / 0.2)  # 0.2m内评分高
        timing_factor = 1.0 if time_to_reach < 1.0 else 0.5
        success_probability = (quality_factor * 0.4 + distance_factor * 0.3 +
                               velocity_alignment * 0.2 + timing_factor * 0.1)

        return {
            "time_to_reach": time_to_reach,
            "hand_response_time": hand_response_time,
            "optimal_close_time": max(0.0, time_to_reach - hand_response_time),
            "distance_to_hand": distance,
            "grasp_quality": grasp_quality,
            "velocity_alignment": velocity_alignment,
            "success_probability": success_probability,
            "should_close": success_probability > 0.7 or distance < 0.05,
            "should_wait": time_to_reach > 0.5 and distance > 0.10,
        }

    def compute_tracking_adjustment(
        self,
        current_hand_x: float,
        current_hand_y: float,
    ) -> tuple[float, float]:
        """
        计算手部追踪调整量

        使用自适应增益控制：
        - 误差大时使用高增益快速追赶
        - 误差小时使用低增益平滑控制
        - 结合速度预测提前调整

        Args:
            current_hand_x: 当前手部x位置
            current_hand_y: 当前手部y位置

        Returns:
            (delta_x, delta_y) 调整量
        """
        if not self.launched:
            return (0.0, 0.0)

        ball_pos = self.get_ball_position()
        ball_vel = self.get_ball_velocity()

        # 计算当前误差
        error_x = ball_pos[0] - current_hand_x
        error_y = ball_pos[1] - current_hand_y
        error_mag = np.sqrt(error_x**2 + error_y**2)

        # 自适应增益：根据误差大小调整增益
        # 目标：保持误差 < 5cm
        # 误差 > 0.08m: 使用高增益(2x)快速追赶
        # 误差 > 0.05m: 使用中高增益(1.5x)
        # 误差 < 0.03m: 使用低增益(0.9x)平滑控制
        if error_mag > 0.08:
            adaptive_gain = self.tracking_gain * 2.0
        elif error_mag > 0.05:
            adaptive_gain = self.tracking_gain * 1.5
        elif error_mag > 0.03:
            adaptive_gain = self.tracking_gain * 1.0
        else:
            adaptive_gain = self.tracking_gain * 0.9  # 平滑控制

        # 速度预测：提前预判球的位置
        speed = np.linalg.norm(ball_vel[:2])
        if speed > 0.01:
            # 使用time_horizon进行预测
            predict_time = min(self.time_horizon, 0.3)
            lead_x = ball_vel[0] * predict_time
            lead_y = ball_vel[1] * predict_time
            # 混合：当前误差 + 预测误差
            error_x = error_x * 0.6 + lead_x * 0.4
            error_y = error_y * 0.6 + lead_y * 0.4

        # 应用自适应增益
        adjustment_x = error_x * adaptive_gain
        adjustment_y = error_y * adaptive_gain

        # 限制最大调整量
        adjustment = np.array([adjustment_x, adjustment_y])
        adjustment_mag = np.linalg.norm(adjustment)
        if adjustment_mag > self.max_adjustment:
            adjustment = adjustment / adjustment_mag * self.max_adjustment

        # 更新追踪误差统计
        self.stats.tracking_error_sum += error_mag
        self.stats.tracking_samples += 1
        self.stats.max_tracking_error = max(self.stats.max_tracking_error, error_mag)

        return (float(adjustment[0]), float(adjustment[1]))

    def is_ball_in_grasp_zone(
        self,
        hand_pos: np.ndarray | None = None,
        grasp_threshold: float | None = None,
    ) -> bool:
        """
        判断球是否进入抓取范围

        Args:
            hand_pos: 手部位置，默认使用手掌位置
            grasp_threshold: 抓取阈值，默认使用配置的阈值

        Returns:
            True如果球在抓取范围内
        """
        if hand_pos is None:
            hand_pos = self.get_palm_position()

        if grasp_threshold is None:
            grasp_threshold = self.grasp_threshold

        ball_pos = self.get_ball_position()
        distance = np.linalg.norm(ball_pos[:2] - hand_pos[:2])
        return distance < grasp_threshold

    def get_grasp_quality(self, hand_pos: np.ndarray | None = None) -> float:
        """
        评估抓取质量 (0-1)

        基于球与手掌中心的对齐程度。
        1.0 = 完美对齐
        0.0 = 完全超出范围

        Args:
            hand_pos: 手部位置

        Returns:
            抓取质量分数
        """
        if hand_pos is None:
            hand_pos = self.get_palm_position()

        ball_pos = self.get_ball_position()
        distance = np.linalg.norm(ball_pos[:2] - hand_pos[:2])

        # 质量评分曲线
        if distance < 0.03:
            return 1.0
        elif distance < 0.08:
            return 1.0 - (distance - 0.03) / 0.05 * 0.5
        else:
            return max(0.0, 0.5 - (distance - 0.08) / 0.1 * 0.5)

    def check_contact(self) -> bool:
        """
        检查是否发生接触

        通过比较当前球位置和手掌位置来判断

        Returns:
            True如果检测到接触
        """
        palm_pos = self.get_palm_position()
        ball_pos = self.get_ball_position()

        # 简单的距离判断
        distance = np.linalg.norm(ball_pos - palm_pos)
        return distance < 0.10  # 10cm范围内

    def get_tracking_stats(self) -> dict:
        """
        获取追踪统计数据

        Returns:
            包含追踪统计信息的字典
        """
        mean_error = (
            self.stats.tracking_error_sum / self.stats.tracking_samples
            if self.stats.tracking_samples > 0
            else 0.0
        )

        return {
            "launch_time": self.stats.launch_time,
            "first_contact_time": self.stats.first_contact_time,
            "catch_time": self.stats.catch_time,
            "mean_tracking_error_m": round(mean_error, 5),
            "max_tracking_error_m": round(self.stats.max_tracking_error, 5),
            "tracking_samples": self.stats.tracking_samples,
        }


def get_joint_limits(model, joint_name: str) -> tuple[float, float]:
    """
    获取关节的限制范围

    Args:
        model: MuJoCo模型
        joint_name: 关节名称

    Returns:
        (min, max) 关节范围
    """
    import mujoco

    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
    if jid < 0:
        raise ValueError(f"Joint '{joint_name}' not found")

    if model.jnt_limited[jid]:
        return (float(model.jnt_range[jid][0]), float(model.jnt_range[jid][1]))
    else:
        # 返回默认值
        return (-1.0, 1.0)


def clamp_to_range(value: float, min_val: float, max_val: float) -> float:
    """限制值在范围内"""
    return float(np.clip(value, min_val, max_val))


def interpolate_pose(
    pose1: dict[str, float],
    pose2: dict[str, float],
    alpha: float,
) -> dict[str, float]:
    """
    在两个姿态之间插值

    Args:
        pose1: 起始姿态
        pose2: 目标姿态
        alpha: 插值因子 [0, 1]

    Returns:
        插值后的姿态
    """
    result = {}
    for joint_name in FINGER_JOINTS:
        if joint_name in pose1 and joint_name in pose2:
            result[joint_name] = float(pose1[joint_name] * (1.0 - alpha) + pose2[joint_name] * alpha)
        elif joint_name in pose1:
            result[joint_name] = pose1[joint_name]
        elif joint_name in pose2:
            result[joint_name] = pose2[joint_name]
    return result


def merge_hand_pose(
    base: dict[str, float],
    hand_x: float,
    hand_y: float,
    hand_z: float,
    wrist_yaw: float = 0.0,
    wrist_pitch: float = 0.0,
    wrist_roll: float = 0.0,
) -> dict[str, float]:
    """
    合并手部位置和姿态

    Args:
        base: 基础姿态(手指关节)
        hand_x, hand_y, hand_z: 手部滑动位置
        wrist_yaw, wrist_pitch, wrist_roll: 腕部旋转

    Returns:
        完整的姿态目标
    """
    result = dict(base)
    result["hand_x"] = hand_x
    result["hand_y"] = hand_y
    result["hand_z"] = hand_z
    result["wrist_yaw"] = wrist_yaw
    result["wrist_pitch"] = wrist_pitch
    result["wrist_roll"] = wrist_roll
    return result
