"""
multi_worker_monitor.py
Orchestrates independent ShiftMonitor and ProductivityTracker instances per worker.
Consumes upstream worker ID + stereo-tracked joint angles & modifiers,
and generates real-time floor-wide ergonomic safety & productivity summaries.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from .rula_assessment import RULAAssessment, RULAResult, RiskLevel
from .shift_monitor import ShiftMonitor, WorkerRiskAlert, ShiftSummary
from .productivity_tracker import ProductivityTracker, CycleMetrics


@dataclass
class WorkerStatus:
    """Current combined safety and productivity status for a single worker."""
    worker_id: str
    last_update_timestamp: float
    current_rula_score: int
    current_risk_level: RiskLevel
    action_level: int
    action_description: str
    current_sustained_seconds: float
    active_alert: Optional[Dict[str, Any]]
    total_alerts_count: int
    shift_summary: Dict[str, Any]
    productivity_metrics: Dict[str, Any]
    joint_angles: Dict[str, float]
    modifiers: Dict[str, bool]
    latest_rula_result: RULAResult

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "last_update_timestamp": round(self.last_update_timestamp, 2),
            "current_rula_score": self.current_rula_score,
            "current_risk_level": self.current_risk_level.value,
            "action_level": self.action_level,
            "action_description": self.action_description,
            "current_sustained_seconds": round(self.current_sustained_seconds, 2),
            "active_alert": self.active_alert,
            "total_alerts_count": self.total_alerts_count,
            "shift_summary": self.shift_summary,
            "productivity_metrics": self.productivity_metrics,
            "joint_angles": self.joint_angles,
            "modifiers": self.modifiers,
        }


@dataclass
class FloorSummary:
    """Consolidated safety and productivity summary across the entire factory floor."""
    timestamp: float
    total_workers_tracked: int
    critical_risk_count: int
    critical_worker_ids: List[str]
    warning_risk_count: int
    warning_worker_ids: List[str]
    safe_worker_ids: List[str]
    safe_count: int
    total_active_alerts: int
    active_alert_worker_ids: List[str]
    floor_average_rula_score: float
    floor_total_cycles_completed: int
    floor_average_cycles_per_hour: float
    workers: Dict[str, WorkerStatus]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": round(self.timestamp, 2),
            "total_workers_tracked": self.total_workers_tracked,
            "critical_risk_count": self.critical_risk_count,
            "critical_worker_ids": self.critical_worker_ids,
            "warning_risk_count": self.warning_risk_count,
            "warning_worker_ids": self.warning_worker_ids,
            "safe_count": self.safe_count,
            "safe_worker_ids": self.safe_worker_ids,
            "total_active_alerts": self.total_active_alerts,
            "active_alert_worker_ids": self.active_alert_worker_ids,
            "floor_average_rula_score": round(self.floor_average_rula_score, 2),
            "floor_total_cycles_completed": self.floor_total_cycles_completed,
            "floor_average_cycles_per_hour": round(self.floor_average_cycles_per_hour, 1),
            "workers": {wid: w.to_dict() for wid, w in self.workers.items()},
        }


class MultiWorkerMonitor:
    """
    Multi-worker factory floor ergonomic and productivity orchestrator.
    Maintains independent ShiftMonitor and ProductivityTracker instances per worker.
    """

    def __init__(
        self,
        sustained_alert_threshold_seconds: float = 120.0,
        cycle_joint_name: str = "elbow_flexion",
        min_cycle_duration_seconds: float = 1.0,
    ):
        self.sustained_threshold = sustained_alert_threshold_seconds
        self.cycle_joint_name = cycle_joint_name
        self.min_cycle_duration = min_cycle_duration_seconds

        self.shift_monitors: Dict[str, ShiftMonitor] = {}
        self.productivity_trackers: Dict[str, ProductivityTracker] = {}
        self.latest_worker_statuses: Dict[str, WorkerStatus] = {}
        self.last_floor_timestamp: float = 0.0

    def _get_or_create_worker(self, worker_id: str):
        if worker_id not in self.shift_monitors:
            self.shift_monitors[worker_id] = ShiftMonitor(
                worker_id=worker_id,
                sustained_threshold_seconds=self.sustained_threshold,
            )
            self.productivity_trackers[worker_id] = ProductivityTracker(
                joint_name=self.cycle_joint_name,
                min_cycle_duration_seconds=self.min_cycle_duration,
            )

    def update_worker(
        self,
        timestamp: float,
        worker_id: str,
        joint_angles: Dict[str, float],
        modifiers: Optional[Dict[str, bool]] = None,
    ) -> Tuple[RULAResult, Optional[WorkerRiskAlert], WorkerStatus]:
        """
        Process a single worker frame from stereo vision stream.
        
        Args:
            timestamp: Epoch timestamp in seconds.
            worker_id: Identifier string (e.g. "WRK-001").
            joint_angles: Dict with keys like "shoulder_flexion", "elbow_flexion", "wrist_flexion", "neck_flexion", "trunk_flexion".
            modifiers: Optional dict of booleans (e.g. "shoulder_raised", "arm_abducted", "neck_twisted", etc.)

        Returns:
            Tuple of (RULAResult, optional new WorkerRiskAlert, WorkerStatus).
        """
        self._get_or_create_worker(worker_id)
        mods = modifiers or {}

        # 1. Deterministic RULA Evaluation
        rula_res = RULAAssessment.evaluate(
            shoulder_flexion=joint_angles.get("shoulder_flexion", 10.0),
            elbow_flexion=joint_angles.get("elbow_flexion", 90.0),
            wrist_flexion=joint_angles.get("wrist_flexion", 0.0),
            neck_flexion=joint_angles.get("neck_flexion", 5.0),
            trunk_flexion=joint_angles.get("trunk_flexion", 0.0),
            shoulder_raised=mods.get("shoulder_raised", False),
            arm_abducted=mods.get("arm_abducted", False),
            arm_supported=mods.get("arm_supported", False),
            arm_across_midline=mods.get("arm_across_midline", False),
            wrist_deviation=mods.get("wrist_deviation", False),
            wrist_twist_end=mods.get("wrist_twist_end", False),
            neck_twisted=mods.get("neck_twisted", False),
            neck_side_bend=mods.get("neck_side_bend", False),
            trunk_twisted=mods.get("trunk_twisted", False),
            trunk_side_bend=mods.get("trunk_side_bend", False),
            legs_balanced=mods.get("legs_balanced", True),
            muscle_use=mods.get("muscle_use", 0),
            force_load=mods.get("force_load", 0),
        )

        # 2. Update Shift Monitor (Sustained Alert Invariant)
        shift_mon = self.shift_monitors[worker_id]
        new_alert = shift_mon.update(timestamp=timestamp, rula_result=rula_res)

        # 3. Update Productivity Tracker (Repetitive Cycle Detection)
        prod_track = self.productivity_trackers[worker_id]
        cycle_angle = joint_angles.get(self.cycle_joint_name, joint_angles.get("elbow_flexion", 90.0))
        prod_track.update(timestamp=timestamp, angle=cycle_angle)

        # 4. Consolidate Worker Status
        shift_sum = shift_mon.get_summary()
        prod_metrics = prod_track.get_metrics(current_time=timestamp)

        status = WorkerStatus(
            worker_id=worker_id,
            last_update_timestamp=timestamp,
            current_rula_score=rula_res.final_score,
            current_risk_level=rula_res.risk_level,
            action_level=rula_res.action_level,
            action_description=rula_res.action_description,
            current_sustained_seconds=shift_mon.get_current_sustained_duration(timestamp),
            active_alert=shift_mon.active_alert.to_dict() if shift_mon.active_alert else None,
            total_alerts_count=len(shift_mon.alerts),
            shift_summary=shift_sum.to_dict(),
            productivity_metrics=prod_metrics.to_dict(),
            joint_angles=joint_angles,
            modifiers=mods,
            latest_rula_result=rula_res,
        )

        self.latest_worker_statuses[worker_id] = status
        self.last_floor_timestamp = max(self.last_floor_timestamp, timestamp)

        return rula_res, new_alert, status

    def get_floor_summary(self, current_time: Optional[float] = None) -> FloorSummary:
        """
        Generate floor-wide aggregate summary across all active workers.
        """
        now = current_time if current_time is not None else self.last_floor_timestamp

        critical_workers: List[str] = []
        warning_workers: List[str] = []
        safe_workers: List[str] = []
        active_alert_workers: List[str] = []

        total_rula_score = 0.0
        total_cycles = 0
        total_rate = 0.0

        for wid, status in self.latest_worker_statuses.items():
            lvl = status.current_risk_level
            if lvl == RiskLevel.CRITICAL:
                critical_workers.append(wid)
            elif lvl == RiskLevel.WARNING:
                warning_workers.append(wid)
            else:
                safe_workers.append(wid)

            if status.active_alert is not None:
                active_alert_workers.append(wid)

            total_rula_score += status.current_rula_score
            total_cycles += status.productivity_metrics.get("cycles_completed", 0)
            total_rate += status.productivity_metrics.get("cycles_per_hour", 0.0)

        num_workers = len(self.latest_worker_statuses)
        avg_rula = (total_rula_score / num_workers) if num_workers > 0 else 0.0
        avg_rate = (total_rate / num_workers) if num_workers > 0 else 0.0

        return FloorSummary(
            timestamp=now,
            total_workers_tracked=num_workers,
            critical_risk_count=len(critical_workers),
            critical_worker_ids=critical_workers,
            warning_risk_count=len(warning_workers),
            warning_worker_ids=warning_workers,
            safe_count=len(safe_workers),
            safe_worker_ids=safe_workers,
            total_active_alerts=len(active_alert_workers),
            active_alert_worker_ids=active_alert_workers,
            floor_average_rula_score=avg_rula,
            floor_total_cycles_completed=total_cycles,
            floor_average_cycles_per_hour=avg_rate,
            workers=self.latest_worker_statuses,
        )


if __name__ == "__main__":
    import math

    print("=" * 60)
    print("Testing Multi-Worker Monitor Module")
    print("=" * 60)

    monitor = MultiWorkerMonitor(sustained_alert_threshold_seconds=120.0)

    # Simulate 3 workers on the floor:
    # WRK-101: Safe ergonomic posture, steady productivity
    # WRK-102: Moderate awkward posture (Warning)
    # WRK-103: Severe awkward posture (Critical)

    t = 0.0
    for step in range(15):
        t = step * 10.0

        # Worker 1: Safe
        monitor.update_worker(
            timestamp=t,
            worker_id="WRK-101",
            joint_angles={
                "shoulder_flexion": 15.0,
                "elbow_flexion": 85.0 + 35.0 * math.sin(0.5 * t),
                "wrist_flexion": 0.0,
                "neck_flexion": 8.0,
                "trunk_flexion": 0.0,
            },
        )

        # Worker 2: Warning
        monitor.update_worker(
            timestamp=t,
            worker_id="WRK-102",
            joint_angles={
                "shoulder_flexion": 55.0,
                "elbow_flexion": 115.0 + 20.0 * math.sin(0.4 * t),
                "wrist_flexion": 15.0,
                "neck_flexion": 15.0,
                "trunk_flexion": 30.0,
            },
            modifiers={"arm_abducted": True},
        )

        # Worker 3: Critical
        monitor.update_worker(
            timestamp=t,
            worker_id="WRK-103",
            joint_angles={
                "shoulder_flexion": 110.0,
                "elbow_flexion": 125.0,
                "wrist_flexion": 30.0,
                "neck_flexion": 30.0,
                "trunk_flexion": 65.0,
            },
            modifiers={"shoulder_raised": True, "arm_abducted": True, "trunk_twisted": True},
        )

    summary = monitor.get_floor_summary()
    print(f"Floor Summary at t={summary.timestamp}s:")
    print(f"  Total Workers: {summary.total_workers_tracked}")
    print(f"  Critical Count: {summary.critical_risk_count} (IDs: {summary.critical_worker_ids})")
    print(f"  Warning Count: {summary.warning_risk_count} (IDs: {summary.warning_worker_ids})")
    print(f"  Safe Count: {summary.safe_count} (IDs: {summary.safe_worker_ids})")
    print(f"  Floor Avg RULA Score: {summary.floor_average_rula_score:.2f}")
    print(f"  Total Active Alerts: {summary.total_active_alerts} (IDs: {summary.active_alert_worker_ids})")

    assert summary.total_workers_tracked == 3
    assert "WRK-103" in summary.critical_worker_ids
    assert "WRK-102" in summary.warning_worker_ids
    assert "WRK-101" in summary.safe_worker_ids
    assert summary.critical_risk_count == 1
    assert summary.warning_risk_count == 1
    assert summary.safe_count == 1
    assert summary.total_active_alerts == 1  # WRK-103 has been critical for 140s (> 120s)

    print("ALL MULTI-WORKER MONITOR INLINE TESTS PASSED SUCCESSFULLY!")
