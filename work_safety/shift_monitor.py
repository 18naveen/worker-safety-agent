"""
shift_monitor.py
Tracks ergonomic risk continuously through a work shift for a single worker.
Enforces the sustained-risk alerting invariant (default: 120+ continuous seconds at warning/critical),
rejects momentary transient spikes, handles first-sample initialization gracefully,
and computes cumulative shift metrics & exposure time distributions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from .rula_assessment import RULAAssessment, RULAResult, RiskLevel


@dataclass
class WorkerRiskAlert:
    """Represents an alert triggered by sustained ergonomic risk."""
    alert_id: str
    worker_id: str
    start_timestamp: float           # Epoch seconds when elevated risk began
    trigger_timestamp: float         # Epoch seconds when threshold was reached
    risk_level: RiskLevel            # RiskLevel.WARNING or RiskLevel.CRITICAL
    sustained_duration_seconds: float
    trigger_score: int
    resolved: bool = False
    resolved_timestamp: Optional[float] = None
    total_duration_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "worker_id": self.worker_id,
            "start_timestamp": self.start_timestamp,
            "trigger_timestamp": self.trigger_timestamp,
            "risk_level": self.risk_level.value,
            "sustained_duration_seconds": round(self.sustained_duration_seconds, 2),
            "trigger_score": self.trigger_score,
            "resolved": self.resolved,
            "resolved_timestamp": self.resolved_timestamp,
            "total_duration_seconds": round(self.total_duration_seconds, 2) if self.total_duration_seconds else None,
        }


@dataclass
class ShiftSummary:
    """Summary of ergonomic risk distribution and alert statistics over a shift."""
    worker_id: str
    total_samples: int
    total_duration_seconds: float
    time_safe_seconds: float
    time_warning_seconds: float
    time_critical_seconds: float
    percent_safe: float
    percent_warning: float
    percent_critical: float
    average_rula_score: float
    max_rula_score: int
    total_alerts: int
    active_alert: Optional[WorkerRiskAlert]
    current_risk_level: RiskLevel
    current_sustained_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "total_samples": self.total_samples,
            "total_duration_seconds": round(self.total_duration_seconds, 2),
            "time_safe_seconds": round(self.time_safe_seconds, 2),
            "time_warning_seconds": round(self.time_warning_seconds, 2),
            "time_critical_seconds": round(self.time_critical_seconds, 2),
            "percent_safe": round(self.percent_safe, 2),
            "percent_warning": round(self.percent_warning, 2),
            "percent_critical": round(self.percent_critical, 2),
            "average_rula_score": round(self.average_rula_score, 2),
            "max_rula_score": self.max_rula_score,
            "total_alerts": self.total_alerts,
            "active_alert": self.active_alert.to_dict() if self.active_alert else None,
            "current_risk_level": self.current_risk_level.value,
            "current_sustained_seconds": round(self.current_sustained_seconds, 2),
        }


class ShiftMonitor:
    """
    Monitors a single worker's ergonomic posture across continuous time.
    Tracks state transitions, aggregates exposure time in each risk zone,
    and fires alerts ONLY when risk level is sustained for >= sustained_threshold_seconds.
    """

    def __init__(
        self,
        worker_id: str,
        sustained_threshold_seconds: float = 120.0,
    ):
        self.worker_id = worker_id
        self.sustained_threshold_seconds = float(sustained_threshold_seconds)

        # State tracking
        self.initialized: bool = False
        self.last_timestamp: Optional[float] = None
        self.last_result: Optional[RULAResult] = None
        self.current_risk_level: Optional[RiskLevel] = None

        # Sustained elevated risk window tracking
        self.elevated_start_timestamp: Optional[float] = None
        self.elevated_risk_level: Optional[RiskLevel] = None
        self.active_alert: Optional[WorkerRiskAlert] = None
        self.alerts: List[WorkerRiskAlert] = []

        # Time accumulation
        self.total_samples: int = 0
        self.total_duration_seconds: float = 0.0
        self.time_safe_seconds: float = 0.0
        self.time_warning_seconds: float = 0.0
        self.time_critical_seconds: float = 0.0
        self.score_sum: float = 0.0
        self.max_score: int = 0
        self._alert_counter: int = 0

    def update(
        self,
        timestamp: float,
        rula_result: RULAResult,
    ) -> Optional[WorkerRiskAlert]:
        """
        Process a new timestamped RULA assessment sample for this worker.
        
        Args:
            timestamp: Epoch timestamp in seconds (float).
            rula_result: The evaluated RULAResult instance.

        Returns:
            WorkerRiskAlert if a new alert was triggered on this frame, else None.
        """
        new_alert_triggered: Optional[WorkerRiskAlert] = None
        current_level = rula_result.risk_level
        score = rula_result.final_score

        self.total_samples += 1
        self.score_sum += score
        if score > self.max_score:
            self.max_score = score

        # Handle very first sample initialization
        if not self.initialized:
            self.initialized = True
            self.last_timestamp = timestamp
            self.last_result = rula_result
            self.current_risk_level = current_level

            # If starting in elevated risk, begin tracking sustained duration
            if current_level in (RiskLevel.WARNING, RiskLevel.CRITICAL):
                self.elevated_start_timestamp = timestamp
                self.elevated_risk_level = current_level
            return None

        # Compute delta time since last frame
        dt = max(0.0, timestamp - (self.last_timestamp or timestamp))
        self.total_duration_seconds += dt

        # Accumulate time in the previous state for the elapsed duration dt
        prev_level = self.current_risk_level or current_level
        if prev_level == RiskLevel.SAFE:
            self.time_safe_seconds += dt
        elif prev_level == RiskLevel.WARNING:
            self.time_warning_seconds += dt
        elif prev_level == RiskLevel.CRITICAL:
            self.time_critical_seconds += dt

        # Update current risk level
        self.current_risk_level = current_level
        self.last_timestamp = timestamp
        self.last_result = rula_result

        # Check sustained risk transitions
        if current_level in (RiskLevel.WARNING, RiskLevel.CRITICAL):
            # Worker is in an elevated risk posture
            if self.elevated_start_timestamp is None:
                # Fresh start of elevated risk
                self.elevated_start_timestamp = timestamp
                self.elevated_risk_level = current_level
            else:
                # If level escalated from WARNING to CRITICAL during the window, escalate tracked level
                if current_level == RiskLevel.CRITICAL:
                    self.elevated_risk_level = RiskLevel.CRITICAL

                sustained_duration = timestamp - self.elevated_start_timestamp
                # Check if threshold reached and no active alert yet
                if (
                    sustained_duration >= self.sustained_threshold_seconds
                    and self.active_alert is None
                ):
                    self._alert_counter += 1
                    alert = WorkerRiskAlert(
                        alert_id=f"ALERT-{self.worker_id}-{self._alert_counter:04d}",
                        worker_id=self.worker_id,
                        start_timestamp=self.elevated_start_timestamp,
                        trigger_timestamp=timestamp,
                        risk_level=self.elevated_risk_level or current_level,
                        sustained_duration_seconds=sustained_duration,
                        trigger_score=score,
                    )
                    self.active_alert = alert
                    self.alerts.append(alert)
                    new_alert_triggered = alert
                elif self.active_alert is not None:
                    # Update active alert sustained duration
                    self.active_alert.sustained_duration_seconds = sustained_duration
                    if current_level == RiskLevel.CRITICAL:
                        self.active_alert.risk_level = RiskLevel.CRITICAL
        else:
            # Worker returned to SAFE posture -> reset sustained risk window
            if self.active_alert is not None:
                # Resolve the active alert
                self.active_alert.resolved = True
                self.active_alert.resolved_timestamp = timestamp
                self.active_alert.total_duration_seconds = (
                    timestamp - self.active_alert.start_timestamp
                )
                self.active_alert = None

            self.elevated_start_timestamp = None
            self.elevated_risk_level = None

        return new_alert_triggered

    def get_current_sustained_duration(self, current_time: Optional[float] = None) -> float:
        """Get seconds of continuous elevated risk currently accumulated."""
        if self.elevated_start_timestamp is None:
            return 0.0
        now = current_time if current_time is not None else (self.last_timestamp or 0.0)
        return max(0.0, now - self.elevated_start_timestamp)

    def get_summary(self) -> ShiftSummary:
        """Generate a complete shift summary dataclass."""
        total_time = max(1e-6, self.total_duration_seconds)
        avg_score = (self.score_sum / self.total_samples) if self.total_samples > 0 else 0.0

        return ShiftSummary(
            worker_id=self.worker_id,
            total_samples=self.total_samples,
            total_duration_seconds=self.total_duration_seconds,
            time_safe_seconds=self.time_safe_seconds,
            time_warning_seconds=self.time_warning_seconds,
            time_critical_seconds=self.time_critical_seconds,
            percent_safe=(self.time_safe_seconds / total_time) * 100.0,
            percent_warning=(self.time_warning_seconds / total_time) * 100.0,
            percent_critical=(self.time_critical_seconds / total_time) * 100.0,
            average_rula_score=avg_score,
            max_rula_score=self.max_score,
            total_alerts=len(self.alerts),
            active_alert=self.active_alert,
            current_risk_level=self.current_risk_level or RiskLevel.SAFE,
            current_sustained_seconds=self.get_current_sustained_duration(),
        )


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Shift Monitor Module (Sustained Risk Alert Invariant)")
    print("=" * 60)

    monitor = ShiftMonitor(worker_id="WRK-001", sustained_threshold_seconds=120.0)

    # Reusable synthetic RULA results
    safe_result = RULAAssessment.evaluate(shoulder_flexion=10.0, trunk_flexion=0.0)
    warning_result = RULAAssessment.evaluate(shoulder_flexion=50.0, trunk_flexion=30.0)
    critical_result = RULAAssessment.evaluate(shoulder_flexion=110.0, trunk_flexion=65.0, shoulder_raised=True)

    t = 0.0

    # 1. Initialization test - first reading at t=0
    alert = monitor.update(timestamp=t, rula_result=safe_result)
    assert alert is None, "First reading should not trigger alert"
    assert monitor.initialized, "Monitor must be initialized on first reading"
    print(f"[t={t}s] First reading processed: Initialized successfully.")

    # 2. Worker works safely for 60 seconds
    for _ in range(6):
        t += 10.0
        monitor.update(timestamp=t, rula_result=safe_result)
    print(f"[t={t}s] 60s of safe work -> Total alerts: {len(monitor.alerts)}, Active: {monitor.active_alert is not None}")
    assert len(monitor.alerts) == 0

    # 3. Test Momentary Spike: 5 seconds of severe CRITICAL posture
    t += 5.0
    spike_alert = monitor.update(timestamp=t, rula_result=critical_result)
    print(f"[t={t}s] Momentary 5s CRITICAL spike -> Alert triggered: {spike_alert is not None}")
    assert spike_alert is None, "Momentary spike must NOT trigger alert!"

    # Return immediately to safe
    t += 5.0
    monitor.update(timestamp=t, rula_result=safe_result)
    print(f"[t={t}s] Back to safe -> Active alert: {monitor.active_alert is not None}, Sustained reset: {monitor.elevated_start_timestamp is None}")
    assert monitor.elevated_start_timestamp is None, "Elevated window must reset after returning to safe"
    assert len(monitor.alerts) == 0, "No alerts should have been recorded for 5s spike"

    # 4. Test Sustained Risk: Worker enters WARNING / CRITICAL posture continuously for 130s (> 120s threshold)
    print("\nStarting sustained elevated posture sequence (t=80s to 210s)...")
    alert_detected_at = None

    # Feed 13 steps of 10 seconds each (130 seconds continuous risk)
    for step in range(1, 14):
        t += 10.0
        step_alert = monitor.update(timestamp=t, rula_result=warning_result)
        sustained = monitor.get_current_sustained_duration()
        if step_alert:
            alert_detected_at = t
            print(f"  -> ALERT TRIGGERED at t={t}s! Sustained: {sustained}s, Alert ID: {step_alert.alert_id}")

    assert alert_detected_at is not None, "Sustained 120s risk MUST trigger an alert!"
    assert monitor.active_alert is not None, "Active alert must remain active while posture persists"
    assert len(monitor.alerts) == 1, "Exactly one alert should have been recorded"
    print(f"Verified: Alert correctly fired at t={alert_detected_at}s (sustained >= 120s).")

    # 5. Worker returns to safe -> Alert resolves
    t += 10.0
    monitor.update(timestamp=t, rula_result=safe_result)
    assert monitor.active_alert is None, "Alert must resolve when returning to safe"
    assert monitor.alerts[0].resolved is True, "Alert resolved flag must be True"
    print(f"[t={t}s] Worker returned to safe. Alert resolved: duration={monitor.alerts[0].total_duration_seconds}s")

    summary = monitor.get_summary()
    print("\nShift Summary:")
    print(f"  Total Duration: {summary.total_duration_seconds}s")
    print(f"  Safe: {summary.percent_safe:.1f}%, Warning: {summary.percent_warning:.1f}%, Critical: {summary.percent_critical:.1f}%")
    print(f"  Avg RULA Score: {summary.average_rula_score:.2f}, Max Score: {summary.max_rula_score}")
    print(f"  Total Alerts: {summary.total_alerts}")

    print("ALL SHIFT MONITOR INLINE TESTS PASSED SUCCESSFULLY!")
