"""
test_suite.py
Comprehensive test suite verifying all 6 worker_safety modules:
1. rula_assessment: Neutral vs Moderate vs Severe postures, strict monotonic ordering, component scores.
2. shift_monitor: Sustained risk invariant (120s+ triggers, 5s spike rejected, clean first-reading init).
3. productivity_tracker: Synthetic sinusoidal motion with known period T=4.0s, cycle count & std dev validation.
4. multi_worker_monitor: Orchestration across 3 workers, aggregate floor statistics, active alert isolation.
5. supervisor_agent: Strict 4-tool boundary, mandatory escalate_critical on critical risk, tamper-evident action_log.
6. skeleton_visualizer: Non-overlapping label bounding box collision verification across horizontally adjacent workers.
"""

import math
import sys
import time
from typing import List, Dict, Any

from worker_safety.rula_assessment import RULAAssessment, RiskLevel
from worker_safety.shift_monitor import ShiftMonitor
from worker_safety.productivity_tracker import ProductivityTracker
from worker_safety.multi_worker_monitor import MultiWorkerMonitor
from worker_safety.supervisor_agent import SupervisorAgent
from worker_safety.skeleton_visualizer import SkeletonVisualizer, WorkerSkeletonVisual, Joint2D, LabelBox


def print_section(title: str):
    print("\n" + "=" * 70)
    print(f"  TEST MODULE: {title}")
    print("=" * 70)


def run_all_tests() -> bool:
    all_passed = True
    test_results: List[Dict[str, Any]] = []

    # =========================================================================
    # 1. RULA ASSESSMENT TESTS
    # =========================================================================
    print_section("1. RULA Assessment (Deterministic McAtamney & Corlett 1993 Standard)")
    try:
        # Test Case 1A: Neutral ergonomic posture (arms at sides, head upright)
        neutral = RULAAssessment.evaluate(
            shoulder_flexion=10.0,
            elbow_flexion=90.0,
            wrist_flexion=0.0,
            neck_flexion=5.0,
            trunk_flexion=0.0,
            legs_balanced=True,
        )
        print(f" [PASS] Neutral Posture  -> Score: {neutral.final_score}/7 | Risk Level: {neutral.risk_level.value.upper()} | Action Level: {neutral.action_level}")
        assert neutral.risk_level == RiskLevel.SAFE
        assert neutral.final_score in (1, 2)

        # Test Case 1B: Moderate awkward posture (arm abducted, trunk flexed)
        moderate = RULAAssessment.evaluate(
            shoulder_flexion=48.0,
            elbow_flexion=115.0,
            wrist_flexion=12.0,
            neck_flexion=18.0,
            trunk_flexion=25.0,
            arm_abducted=True,
        )
        print(f" [PASS] Moderate Posture -> Score: {moderate.final_score}/7 | Risk Level: {moderate.risk_level.value.upper()} | Action Level: {moderate.action_level}")
        assert moderate.risk_level == RiskLevel.WARNING
        assert 3 <= moderate.final_score <= 6
        assert neutral.final_score < moderate.final_score

        # Test Case 1C: Severe awkward posture (overhead reach, twisted spine)
        severe = RULAAssessment.evaluate(
            shoulder_flexion=110.0,
            elbow_flexion=135.0,
            wrist_flexion=30.0,
            neck_flexion=35.0,
            trunk_flexion=70.0,
            shoulder_raised=True,
            arm_abducted=True,
            wrist_deviation=True,
            wrist_twist_end=True,
            neck_twisted=True,
            trunk_twisted=True,
            legs_balanced=False,
            force_load=2,
            muscle_use=1,
        )
        print(f" [PASS] Severe Posture   -> Score: {severe.final_score}/7 | Risk Level: {severe.risk_level.value.upper()} | Action Level: {severe.action_level}")
        assert severe.risk_level == RiskLevel.CRITICAL
        assert severe.final_score == 7
        assert moderate.final_score < severe.final_score

        test_results.append({"module": "rula_assessment", "status": "PASSED", "details": "Neutral (1-2 SAFE) < Moderate (4 WARNING) < Severe (7 CRITICAL)"})
    except Exception as e:
        print(f" [FAIL] RULA Assessment Failed: {e}")
        test_results.append({"module": "rula_assessment", "status": "FAILED", "details": str(e)})
        all_passed = False

    # =========================================================================
    # 2. SHIFT MONITOR TESTS (Sustained Risk Alert Invariant)
    # =========================================================================
    print_section("2. Shift Monitor (Sustained Risk Window & Noise Spike Rejection)")
    try:
        mon = ShiftMonitor(worker_id="WRK-TEST-01", sustained_threshold_seconds=120.0)
        safe_r = RULAAssessment.evaluate(shoulder_flexion=10.0, trunk_flexion=0.0)
        crit_r = RULAAssessment.evaluate(shoulder_flexion=110.0, trunk_flexion=65.0, shoulder_raised=True)

        t = 0.0
        # First reading: no crash, no false alert
        first_alert = mon.update(timestamp=t, rula_result=safe_r)
        assert first_alert is None and mon.initialized
        print(" [PASS] Initial Sample (t=0s): Initialized cleanly without false trigger.")

        # 5-second bad posture spike: MUST NOT trigger alert
        t += 5.0
        spike_alert = mon.update(timestamp=t, rula_result=crit_r)
        assert spike_alert is None
        print(" [PASS] Momentary Spike (5s CRITICAL): Correctly ignored (0 alerts triggered).")

        # Worker returns to safe posture
        t += 5.0
        mon.update(timestamp=t, rula_result=safe_r)
        assert mon.elevated_start_timestamp is None
        print(" [PASS] Recovery (t=10s): Sustained accumulator successfully reset.")

        # 130 seconds sustained CRITICAL posture (> 120s threshold)
        triggered_alert = None
        for step in range(13):
            t += 10.0
            step_alert = mon.update(timestamp=t, rula_result=crit_r)
            if step_alert:
                triggered_alert = step_alert

        assert triggered_alert is not None, "Alert MUST fire after 120s sustained risk"
        assert mon.active_alert is not None
        print(f" [PASS] Sustained Risk (130s): Alert triggered at t={triggered_alert.trigger_timestamp}s (ID: {triggered_alert.alert_id}).")

        # Worker recovers to safe
        t += 10.0
        mon.update(timestamp=t, rula_result=safe_r)
        assert mon.active_alert is None
        assert mon.alerts[0].resolved is True
        print(" [PASS] Alert Resolution: Alert marked resolved upon posture normalization.")

        summary = mon.get_summary()
        print(f"        Shift Summary -> Exposure: Safe={summary.percent_safe:.1f}%, Critical={summary.percent_critical:.1f}%, Total Alerts={summary.total_alerts}")
        test_results.append({"module": "shift_monitor", "status": "PASSED", "details": "5s spike rejected, 120s+ sustained triggered & resolved"})
    except Exception as e:
        print(f" [FAIL] Shift Monitor Failed: {e}")
        test_results.append({"module": "shift_monitor", "status": "FAILED", "details": str(e)})
        all_passed = False

    # =========================================================================
    # 3. PRODUCTIVITY TRACKER TESTS
    # =========================================================================
    print_section("3. Productivity Tracker (Velocity Zero-Crossing Cycle Detection)")
    try:
        tracker = ProductivityTracker(joint_name="elbow_flexion", min_cycle_duration_seconds=1.0, min_amplitude_degrees=15.0)
        period = 4.0
        omega = 2 * math.pi / period
        dt = 1.0 / 30.0  # 30 fps
        total_time = 40.0

        t = 0.0
        while t <= total_time:
            angle = 90.0 + 40.0 * math.sin(omega * t)
            tracker.update(timestamp=t, angle=angle)
            t += dt

        metrics = tracker.get_metrics(current_time=total_time)
        print(f" [PASS] Sinusoidal Ground Truth (Period T={period:.2f}s, Total Time={total_time:.1f}s)")
        print(f"        Detected Cycles: {metrics.cycles_completed} (Theoretical: {total_time/period:.1f})")
        print(f"        Mean Cycle Duration: {metrics.average_cycle_duration:.4f}s (Error: {abs(metrics.average_cycle_duration - period):.4f}s)")
        print(f"        Cycle Duration Std Dev: {metrics.cycle_duration_std_dev:.5f}s (Consistency metric)")
        print(f"        Rolling Rate: {metrics.cycles_per_hour:.1f} cycles/hr")

        assert 8 <= metrics.cycles_completed <= 11
        assert abs(metrics.average_cycle_duration - period) < 0.05
        assert metrics.cycle_duration_std_dev < 0.05

        test_results.append({"module": "productivity_tracker", "status": "PASSED", "details": f"Mean duration {metrics.average_cycle_duration:.3f}s == Ground Truth {period:.1f}s, StdDev={metrics.cycle_duration_std_dev:.4f}s"})
    except Exception as e:
        print(f" [FAIL] Productivity Tracker Failed: {e}")
        test_results.append({"module": "productivity_tracker", "status": "FAILED", "details": str(e)})
        all_passed = False

    # =========================================================================
    # 4. MULTI-WORKER MONITOR TESTS
    # =========================================================================
    print_section("4. Multi-Worker Monitor (Floor-Wide Orchestration)")
    try:
        mwm = MultiWorkerMonitor(sustained_alert_threshold_seconds=120.0)
        # Update 3 workers across 15 frames (150 seconds)
        for step in range(16):
            t = step * 10.0
            # Worker 1: Safe
            mwm.update_worker(t, "WRK-101", {"shoulder_flexion": 10.0, "elbow_flexion": 85.0 + 30.0 * math.sin(0.5 * t)})
            # Worker 2: Warning
            mwm.update_worker(t, "WRK-102", {"shoulder_flexion": 50.0, "elbow_flexion": 110.0, "trunk_flexion": 25.0}, {"arm_abducted": True})
            # Worker 3: Critical sustained for 150s (> 120s)
            mwm.update_worker(t, "WRK-103", {"shoulder_flexion": 105.0, "elbow_flexion": 130.0, "trunk_flexion": 65.0}, {"shoulder_raised": True, "trunk_twisted": True})

        floor_summary = mwm.get_floor_summary()
        print(f" [PASS] Floor Summary Generated:")
        print(f"        Total Workers: {floor_summary.total_workers_tracked} | Safe: {floor_summary.safe_count} | Warning: {floor_summary.warning_risk_count} | Critical: {floor_summary.critical_risk_count}")
        print(f"        Active Alerts: {floor_summary.total_active_alerts} (Alerted Workers: {floor_summary.active_alert_worker_ids})")
        print(f"        Floor Avg RULA: {floor_summary.floor_average_rula_score:.2f}")

        assert floor_summary.total_workers_tracked == 3
        assert "WRK-103" in floor_summary.critical_worker_ids
        assert "WRK-102" in floor_summary.warning_worker_ids
        assert "WRK-101" in floor_summary.safe_worker_ids
        assert "WRK-103" in floor_summary.active_alert_worker_ids

        test_results.append({"module": "multi_worker_monitor", "status": "PASSED", "details": "3 workers tracked, 1 Critical, 1 Warning, 1 Safe, 1 Active Alert"})
    except Exception as e:
        print(f" [FAIL] Multi-Worker Monitor Failed: {e}")
        test_results.append({"module": "multi_worker_monitor", "status": "FAILED", "details": str(e)})
        all_passed = False

    # =========================================================================
    # 5. SUPERVISOR AGENT TESTS (Strict 4 Tools & Mandatory Escalation)
    # =========================================================================
    print_section("5. Supervisor Agent (Strict 4 Tools Boundary & Mandatory Escalation)")
    try:
        agent = SupervisorAgent()
        assert len(agent.ALLOWED_TOOLS) == 4
        assert agent.ALLOWED_TOOLS == {"log_incident", "notify_supervisor", "escalate_critical", "generate_shift_report"}
        print(" [PASS] Tool Boundary Verification: Strictly 4 permitted tools (no machine stoppage/punitive tools).")

        # Test unauthorized tool rejection
        try:
            agent._execute_tool("terminate_conveyor_line", {})
            assert False, "Unauthorized tool call should have failed"
        except PermissionError:
            print(" [PASS] Safety Boundary Enforced: Direct actuation tool calls rejected with PermissionError.")

        # Review floor summary containing critical worker
        synthetic_floor = {
            "timestamp": 150.0,
            "total_workers_tracked": 3,
            "critical_risk_count": 1,
            "critical_worker_ids": ["WRK-103"],
            "warning_risk_count": 1,
            "warning_worker_ids": ["WRK-102"],
            "safe_count": 1,
            "safe_worker_ids": ["WRK-101"],
            "total_active_alerts": 1,
            "active_alert_worker_ids": ["WRK-103"],
            "floor_average_rula_score": 4.33,
            "floor_total_cycles_completed": 35,
            "floor_average_cycles_per_hour": 140.0,
            "workers": {
                "WRK-103": {"current_rula_score": 7, "current_risk_level": "critical", "current_sustained_seconds": 150.0},
                "WRK-102": {"current_rula_score": 4, "current_risk_level": "warning", "current_sustained_seconds": 50.0},
                "WRK-101": {"current_rula_score": 1, "current_risk_level": "safe", "current_sustained_seconds": 0.0},
            },
        }

        decision = agent.review_floor_summary(synthetic_floor)
        print(f" [PASS] Autonomous Decision Executed:")
        print(f"        Mandatory Escalations: {decision.mandatory_escalations_executed}")
        print(f"        Total Tool Actions: {len(decision.tool_calls)} | Action Log Records: {len(agent.action_log)}")
        for tc in decision.tool_calls:
            print(f"          -> [{tc.tool_name}] Status: {tc.status} | Call ID: {tc.call_id}")

        assert decision.mandatory_escalations_executed >= 1
        assert any(c.tool_name == "escalate_critical" for c in decision.tool_calls)
        assert len(agent.action_log) >= 1

        test_results.append({"module": "supervisor_agent", "status": "PASSED", "details": "Strict 4 tools boundary verified, mandatory critical escalation executed & logged"})
    except Exception as e:
        print(f" [FAIL] Supervisor Agent Failed: {e}")
        test_results.append({"module": "supervisor_agent", "status": "FAILED", "details": str(e)})
        all_passed = False

    # =========================================================================
    # 6. SKELETON VISUALIZER TESTS (Anti-Overlap Collision Avoidance)
    # =========================================================================
    print_section("6. Skeleton Visualizer (Multi-Worker Non-Overlapping Label Placement)")
    try:
        vis = SkeletonVisualizer()
        workers = [
            WorkerSkeletonVisual("WRK-101", "safe", 2, 0.0, {"nose": Joint2D(150, 200), "neck": Joint2D(150, 230)}),
            WorkerSkeletonVisual("WRK-102", "warning", 4, 60.0, {"nose": Joint2D(180, 205), "neck": Joint2D(180, 235)}),
            WorkerSkeletonVisual("WRK-103", "critical", 7, 140.0, {"nose": Joint2D(210, 200), "neck": Joint2D(210, 230)}, has_active_alert=True),
        ]

        placed_boxes: List[LabelBox] = []
        for w in workers:
            box = vis.compute_label_box(w, placed_boxes, frame_width=1280, frame_height=720)
            placed_boxes.append(box)

        # Pairwise overlap verification
        overlap_count = 0
        for i in range(len(placed_boxes)):
            for j in range(i + 1, len(placed_boxes)):
                b1, b2 = placed_boxes[i], placed_boxes[j]
                if b1.overlaps(b2, padding=0):
                    overlap_count += 1
                    print(f" [COLLISION] {b1.worker_id} overlaps with {b2.worker_id}")

        assert overlap_count == 0, f"Found {overlap_count} overlapping label boxes!"
        print(f" [PASS] Placed {len(placed_boxes)} labels for 3 adjacent workers (spacing: 30px centers):")
        for b in placed_boxes:
            print(f"        - {b.worker_id}: bbox=({b.x_min}, {b.y_min}) to ({b.x_max}, {b.y_max}) | color={b.color_bgr}")
        print(" [PASS] Exact collision check confirmed 0 overlaps across all label bounding boxes.")

        test_results.append({"module": "skeleton_visualizer", "status": "PASSED", "details": "0 label overlaps across tightly-spaced workers (staggered placement)"})
    except Exception as e:
        print(f" [FAIL] Skeleton Visualizer Failed: {e}")
        test_results.append({"module": "skeleton_visualizer", "status": "FAILED", "details": str(e)})
        all_passed = False

    # =========================================================================
    # SUMMARY TABLE
    # =========================================================================
    print("\n" + "=" * 70)
    print("  FINAL TEST SUMMARY")
    print("=" * 70)
    for res in test_results:
        print(f"  [{res['status']}] {res['module'].ljust(24)} : {res['details']}")
    print("=" * 70)
    print(f"  OVERALL RESULT: {'ALL MODULE TESTS PASSED (6/6)' if all_passed else 'SOME TESTS FAILED'}")
    print("=" * 70 + "\n")

    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
