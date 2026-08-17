"""
productivity_tracker.py
Detects repetitive task cycles (e.g., hand-molding reach/withdraw cycles) from a single joint's
angle time series using zero-crossing detection on angular velocity with noise filtering.
Computes rolling cycle rate (cycles/hour over a recent window), average cycle duration,
and cycle duration standard deviation (consistency metric for fatigue detection).
"""

import math
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class CycleRecord:
    """Represents a completed single ergonomic repetitive task cycle."""
    cycle_index: int
    start_time: float
    end_time: float
    duration: float
    min_angle: float
    max_angle: float
    amplitude: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_index": self.cycle_index,
            "start_time": round(self.start_time, 2),
            "end_time": round(self.end_time, 2),
            "duration": round(self.duration, 2),
            "min_angle": round(self.min_angle, 1),
            "max_angle": round(self.max_angle, 1),
            "amplitude": round(self.amplitude, 1),
        }


@dataclass
class CycleMetrics:
    """Consolidated productivity and cycle consistency metrics."""
    cycles_completed: int
    cycles_per_hour: float              # Rolling recent window rate
    average_cycle_duration: float       # Mean duration of completed cycles in seconds
    cycle_duration_std_dev: float       # Consistency standard deviation in seconds
    min_cycle_duration: float
    max_cycle_duration: float
    current_cycle_elapsed: float        # Seconds elapsed in current uncompleted cycle
    rolling_window_seconds: float
    recent_cycles_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycles_completed": self.cycles_completed,
            "cycles_per_hour": round(self.cycles_per_hour, 1),
            "average_cycle_duration": round(self.average_cycle_duration, 2),
            "cycle_duration_std_dev": round(self.cycle_duration_std_dev, 2),
            "min_cycle_duration": round(self.min_cycle_duration, 2) if self.min_cycle_duration < float('inf') else 0.0,
            "max_cycle_duration": round(self.max_cycle_duration, 2),
            "current_cycle_elapsed": round(self.current_cycle_elapsed, 2),
            "rolling_window_seconds": self.rolling_window_seconds,
            "recent_cycles_count": self.recent_cycles_count,
        }


class ProductivityTracker:
    """
    Tracks repetitive task motion cycles for an individual worker joint angle series.
    Uses smoothed velocity zero-crossing detection where one full cycle consists of
    two consecutive direction reversals (e.g. forward reach peak followed by withdraw valley).
    """

    def __init__(
        self,
        joint_name: str = "elbow_flexion",
        min_cycle_duration_seconds: float = 1.0,
        min_amplitude_degrees: float = 15.0,
        rolling_window_seconds: float = 600.0,  # 10 minute rolling window for rate
    ):
        self.joint_name = joint_name
        self.min_cycle_duration = min_cycle_duration_seconds
        self.min_amplitude = min_amplitude_degrees
        self.rolling_window_seconds = rolling_window_seconds

        # State tracking
        self.prev_timestamp: Optional[float] = None
        self.prev_angle: Optional[float] = None
        self.prev_raw_velocity: Optional[float] = None

        # Reversal detection
        self.last_reversal_time: Optional[float] = None
        self.last_reversal_angle: Optional[float] = None
        self.current_cycle_start_time: Optional[float] = None
        self.reversal_count_in_cycle: int = 0
        self.cycle_min_angle: float = float("inf")
        self.cycle_max_angle: float = float("-inf")

        # History of completed cycles
        self.completed_cycles: List[CycleRecord] = []
        self._total_cycle_count: int = 0

    def update(self, timestamp: float, angle: float) -> Optional[CycleRecord]:
        """
        Feed a new timestamped joint angle sample.
        
        Args:
            timestamp: Epoch seconds (float).
            angle: Joint angle in degrees (float).

        Returns:
            CycleRecord if a full valid cycle was just completed, else None.
        """
        new_cycle: Optional[CycleRecord] = None

        if self.prev_timestamp is None or self.prev_angle is None:
            self.prev_timestamp = timestamp
            self.prev_angle = angle
            self.cycle_min_angle = angle
            self.cycle_max_angle = angle
            return None

        dt = timestamp - self.prev_timestamp
        if dt <= 1e-6:
            return None

        raw_velocity = (angle - self.prev_angle) / dt

        # Update angle extrema
        self.cycle_min_angle = min(self.cycle_min_angle, angle)
        self.cycle_max_angle = max(self.cycle_max_angle, angle)

        # Zero-crossing on velocity: sign changed between prev_raw_velocity and raw_velocity
        if self.prev_raw_velocity is not None:
            # Check for zero crossing (one positive, one negative)
            if (self.prev_raw_velocity * raw_velocity < 0) or (self.prev_raw_velocity != 0 and raw_velocity == 0):
                # Direction reversal (peak or valley reached)
                # Exact zero-crossing time interpolation
                v1 = self.prev_raw_velocity
                v2 = raw_velocity
                denom = (abs(v1) + abs(v2))
                frac = abs(v1) / denom if denom > 1e-6 else 0.5
                reversal_time = self.prev_timestamp + frac * dt
                reversal_angle = self.prev_angle + frac * (angle - self.prev_angle)

                if self.current_cycle_start_time is None:
                    # First reversal becomes the cycle anchor
                    self.current_cycle_start_time = reversal_time
                    self.cycle_min_angle = reversal_angle
                    self.cycle_max_angle = reversal_angle
                    self.reversal_count_in_cycle = 0
                else:
                    self.reversal_count_in_cycle += 1

                    # Two direction reversals = 1 complete cycle (e.g., peak -> valley -> peak)
                    if self.reversal_count_in_cycle >= 2:
                        cycle_duration = reversal_time - self.current_cycle_start_time
                        cycle_amplitude = self.cycle_max_angle - self.cycle_min_angle

                        # Noise filtering: require minimum plausible duration and amplitude
                        if (
                            cycle_duration >= self.min_cycle_duration
                            and cycle_amplitude >= self.min_amplitude
                        ):
                            self._total_cycle_count += 1
                            new_cycle = CycleRecord(
                                cycle_index=self._total_cycle_count,
                                start_time=self.current_cycle_start_time,
                                end_time=reversal_time,
                                duration=cycle_duration,
                                min_angle=self.cycle_min_angle,
                                max_angle=self.cycle_max_angle,
                                amplitude=cycle_amplitude,
                            )
                            self.completed_cycles.append(new_cycle)

                            # Reset baseline for next cycle starting at this exact reversal
                            self.current_cycle_start_time = reversal_time
                            self.cycle_min_angle = reversal_angle
                            self.cycle_max_angle = reversal_angle
                            self.reversal_count_in_cycle = 0
                        else:
                            # Too small / fast: reset cycle anchor to latest reversal
                            self.current_cycle_start_time = reversal_time
                            self.reversal_count_in_cycle = 0

                self.last_reversal_time = reversal_time
                self.last_reversal_angle = reversal_angle

        self.prev_raw_velocity = raw_velocity
        self.prev_timestamp = timestamp
        self.prev_angle = angle
        return new_cycle

    def get_metrics(self, current_time: Optional[float] = None) -> CycleMetrics:
        """Compute rolling productivity metrics over recent window."""
        now = current_time if current_time is not None else (self.prev_timestamp or 0.0)
        total_completed = len(self.completed_cycles)

        if total_completed == 0:
            elapsed = 0.0
            if self.current_cycle_start_time is not None and now >= self.current_cycle_start_time:
                elapsed = now - self.current_cycle_start_time

            return CycleMetrics(
                cycles_completed=0,
                cycles_per_hour=0.0,
                average_cycle_duration=0.0,
                cycle_duration_std_dev=0.0,
                min_cycle_duration=float("inf"),
                max_cycle_duration=0.0,
                current_cycle_elapsed=elapsed,
                rolling_window_seconds=self.rolling_window_seconds,
                recent_cycles_count=0,
            )

        durations = [c.duration for c in self.completed_cycles]
        avg_duration = sum(durations) / len(durations)
        min_dur = min(durations)
        max_dur = max(durations)

        if len(durations) > 1:
            variance = sum((d - avg_duration) ** 2 for d in durations) / (len(durations) - 1)
            std_dev = math.sqrt(variance)
        else:
            std_dev = 0.0

        window_start = now - self.rolling_window_seconds
        recent_cycles = [c for c in self.completed_cycles if c.end_time >= window_start]
        recent_count = len(recent_cycles)

        if recent_count > 0 and self.rolling_window_seconds > 0:
            earliest_time = recent_cycles[0].start_time
            effective_window_seconds = max(1.0, min(self.rolling_window_seconds, now - earliest_time))
            rate_per_hour = (recent_count / effective_window_seconds) * 3600.0
        else:
            rate_per_hour = 0.0

        current_elapsed = 0.0
        if self.current_cycle_start_time is not None:
            current_elapsed = max(0.0, now - self.current_cycle_start_time)

        return CycleMetrics(
            cycles_completed=total_completed,
            cycles_per_hour=rate_per_hour,
            average_cycle_duration=avg_duration,
            cycle_duration_std_dev=std_dev,
            min_cycle_duration=min_dur,
            max_cycle_duration=max_dur,
            current_cycle_elapsed=current_elapsed,
            rolling_window_seconds=self.rolling_window_seconds,
            recent_cycles_count=recent_count,
        )


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Productivity Tracker Module (Repetitive Cycle Detection)")
    print("=" * 60)

    tracker = ProductivityTracker(
        joint_name="elbow_flexion",
        min_cycle_duration_seconds=1.0,
        min_amplitude_degrees=15.0,
        rolling_window_seconds=300.0,
    )

    period = 4.0
    omega = 2 * math.pi / period
    sample_rate_hz = 30.0
    dt = 1.0 / sample_rate_hz
    total_time = 40.0

    detected_cycles = []
    t = 0.0
    while t <= total_time:
        angle = 90.0 + 40.0 * math.sin(omega * t)
        cycle = tracker.update(timestamp=t, angle=angle)
        if cycle:
            detected_cycles.append(cycle)
        t += dt

    metrics = tracker.get_metrics(current_time=total_time)
    print(f"Ground Truth: Period={period:.2f}s, Theoretical Cycles in {total_time}s = {total_time / period:.1f}")
    print(f"Productivity Tracker Output:")
    print(f"  Cycles Completed: {metrics.cycles_completed}")
    print(f"  Average Cycle Duration: {metrics.average_cycle_duration:.4f}s (Expected {period:.2f}s)")
    print(f"  Cycle Duration Std Dev: {metrics.cycle_duration_std_dev:.5f}s")
    print(f"  Cycles / Hour (Rolling): {metrics.cycles_per_hour:.1f}")

    assert 8 <= metrics.cycles_completed <= 11, f"Expected ~9-10 cycles, got {metrics.cycles_completed}"
    assert abs(metrics.average_cycle_duration - period) < 0.05, f"Avg duration {metrics.average_cycle_duration} diverged from ground truth {period}"
    assert metrics.cycle_duration_std_dev < 0.05, f"Std dev {metrics.cycle_duration_std_dev} should be near zero for clean synthetic sine"

    print("ALL PRODUCTIVITY TRACKER INLINE TESTS PASSED SUCCESSFULLY!")
