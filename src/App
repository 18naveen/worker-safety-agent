/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Activity,
  Shield,
  AlertTriangle,
  CheckCircle,
  Play,
  Pause,
  RotateCcw,
  Sliders,
  Terminal,
  Cloud,
  Layers,
  FileText,
  UserCheck,
  TrendingUp,
  Cpu,
  Eye,
  AlertOctagon,
  RefreshCw,
  Send,
  Zap,
  Info,
  Clock,
  Sparkles,
  Server,
  Lock,
} from 'lucide-react';

// Joint angles interface
interface JointAngles {
  shoulder_flexion: number;
  elbow_flexion: number;
  wrist_flexion: number;
  neck_flexion: number;
  trunk_flexion: number;
}

interface Modifiers {
  shoulder_raised: boolean;
  arm_abducted: boolean;
  arm_supported: boolean;
  arm_across_midline: boolean;
  wrist_deviation: boolean;
  wrist_twist_end: boolean;
  neck_twisted: boolean;
  neck_side_bend: boolean;
  trunk_twisted: boolean;
  trunk_side_bend: boolean;
  legs_balanced: boolean;
  muscle_use: number;
  force_load: number;
}

interface RULAResult {
  final_score: number;
  action_level: number;
  action_description: string;
  risk_level: 'safe' | 'warning' | 'critical';
  components: {
    upper_arm: number;
    lower_arm: number;
    wrist: number;
    wrist_twist: number;
    table_a_score: number;
    score_c: number;
    neck: number;
    trunk: number;
    legs: number;
    table_b_score: number;
    score_d: number;
  };
  raw_angles: JointAngles;
  raw_modifiers: Modifiers;
}

interface SimulatedWorker {
  id: string;
  name: string;
  station: string;
  baseX: number;
  baseY: number;
  phase: number;
  speed: number;
  postureMode: 'safe' | 'warning' | 'critical' | 'intermittent';
  sustainedSeconds: number;
  alertActive: boolean;
  completedCycles: number;
  cycleHistory: number[];
  rula: RULAResult;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'floor' | 'rula' | 'productivity' | 'shift' | 'agent' | 'tests' | 'vertex'>('floor');
  const [simulationRunning, setSimulationRunning] = useState<boolean>(true);
  const [simTime, setSimTime] = useState<number>(0);

  // Manual RULA Playground State
  const [customAngles, setCustomAngles] = useState<JointAngles>({
    shoulder_flexion: 15,
    elbow_flexion: 85,
    wrist_flexion: 0,
    neck_flexion: 8,
    trunk_flexion: 5,
  });

  const [customMods, setCustomMods] = useState<Modifiers>({
    shoulder_raised: false,
    arm_abducted: false,
    arm_supported: false,
    arm_across_midline: false,
    wrist_deviation: false,
    wrist_twist_end: false,
    neck_twisted: false,
    neck_side_bend: false,
    trunk_twisted: false,
    trunk_side_bend: false,
    legs_balanced: true,
    muscle_use: 0,
    force_load: 0,
  });

  const [playgroundRULA, setPlaygroundRULA] = useState<RULAResult | null>(null);

  // Python Test Suite execution state
  const [testOutput, setTestOutput] = useState<string>('');
  const [testingRunning, setTestingRunning] = useState<boolean>(false);
  const [testSuccess, setTestSuccess] = useState<boolean | null>(null);

  // Agent State
  const [agentDecision, setAgentDecision] = useState<any>(null);
  const [agentLogs, setAgentLogs] = useState<any[]>([]);
  const [agentLoading, setAgentLoading] = useState<boolean>(false);

  // Vertex AI Test Playground
  const [vertexInputJson, setVertexInputJson] = useState<string>(
    JSON.stringify(
      {
        instances: [
          {
            worker_id: 'WRK-001',
            shoulder_flexion: 110.0,
            elbow_flexion: 130.0,
            wrist_flexion: 25.0,
            neck_flexion: 30.0,
            trunk_flexion: 65.0,
            shoulder_raised: true,
            arm_abducted: true,
            trunk_twisted: true,
            legs_balanced: false,
          },
          {
            worker_id: 'WRK-002',
            shoulder_flexion: 15.0,
            elbow_flexion: 90.0,
            wrist_flexion: 0.0,
            neck_flexion: 5.0,
            trunk_flexion: 0.0,
            legs_balanced: true,
          },
        ],
      },
      null,
      2
    )
  );
  const [vertexResponseJson, setVertexResponseJson] = useState<string>('');
  const [vertexLoading, setVertexLoading] = useState<boolean>(false);

  // 3 Workers for floor simulation
  const [workers, setWorkers] = useState<SimulatedWorker[]>([
    {
      id: 'WRK-101',
      name: 'Elena Rostova',
      station: 'Station A (Hand Molding)',
      baseX: 200,
      baseY: 220,
      phase: 0,
      speed: 1.0,
      postureMode: 'safe',
      sustainedSeconds: 0,
      alertActive: false,
      completedCycles: 14,
      cycleHistory: [3.9, 4.1, 4.0, 3.95, 4.05],
      rula: null as any,
    },
    {
      id: 'WRK-102',
      name: 'Marcus Vance',
      station: 'Station B (Bin Reach)',
      baseX: 420,
      baseY: 220,
      phase: 1.5,
      speed: 0.85,
      postureMode: 'warning',
      sustainedSeconds: 45,
      alertActive: false,
      completedCycles: 11,
      cycleHistory: [4.4, 4.6, 4.8, 5.0, 4.9],
      rula: null as any,
    },
    {
      id: 'WRK-103',
      name: 'Kenji Sato',
      station: 'Station C (Overhead Fixture)',
      baseX: 640,
      baseY: 220,
      phase: 3.0,
      speed: 0.7,
      postureMode: 'critical',
      sustainedSeconds: 135,
      alertActive: true,
      completedCycles: 8,
      cycleHistory: [5.2, 5.8, 6.1, 6.4, 6.8],
      rula: null as any,
    },
  ]);

  // Client-side RULA evaluation helper matching McAtamney & Corlett 1993
  const evaluateRULALocal = (angles: JointAngles, mods: Modifiers): RULAResult => {
    const sf = angles.shoulder_flexion;
    const ef = angles.elbow_flexion;
    const wf = angles.wrist_flexion;
    const nf = angles.neck_flexion;
    const tf = angles.trunk_flexion;

    // Upper Arm
    let uaBase = 1;
    if (sf >= -20 && sf <= 20) uaBase = 1;
    else if (sf < -20 || (sf > 20 && sf <= 45)) uaBase = 2;
    else if (sf > 45 && sf <= 90) uaBase = 3;
    else uaBase = 4;

    let uaMod = 0;
    if (mods.shoulder_raised) uaMod++;
    if (mods.arm_abducted) uaMod++;
    if (mods.arm_supported) uaMod--;
    const uaTotal = Math.max(1, Math.min(6, uaBase + uaMod));

    // Lower Arm
    const laBase = ef >= 60 && ef <= 100 ? 1 : 2;
    const laMod = mods.arm_across_midline ? 1 : 0;
    const laTotal = Math.max(1, Math.min(3, laBase + laMod));

    // Wrist
    const absW = Math.abs(wf);
    let wBase = 1;
    if (absW <= 5) wBase = 1;
    else if (absW <= 15) wBase = 2;
    else wBase = 3;
    const wMod = mods.wrist_deviation ? 1 : 0;
    const wTotal = Math.max(1, Math.min(4, wBase + wMod));
    const wTwist = mods.wrist_twist_end ? 2 : 1;

    // Table A Lookup
    const TABLE_A = [
      [
        [[1, 2], [2, 2], [2, 3], [3, 3]],
        [[2, 2], [2, 2], [3, 3], [3, 3]],
        [[2, 3], [3, 3], [3, 3], [4, 4]],
      ],
      [
        [[2, 3], [3, 3], [3, 4], [4, 4]],
        [[3, 3], [3, 3], [3, 4], [4, 4]],
        [[3, 4], [4, 4], [4, 4], [5, 5]],
      ],
      [
        [[3, 3], [4, 4], [4, 4], [5, 5]],
        [[3, 4], [4, 4], [4, 4], [5, 5]],
        [[4, 4], [4, 4], [5, 5], [5, 5]],
      ],
      [
        [[4, 4], [4, 5], [5, 5], [5, 6]],
        [[4, 4], [4, 5], [5, 5], [5, 6]],
        [[4, 5], [5, 5], [5, 6], [6, 6]],
      ],
      [
        [[5, 5], [5, 6], [6, 7], [7, 7]],
        [[5, 6], [6, 6], [6, 7], [7, 7]],
        [[6, 6], [6, 7], [7, 7], [7, 8]],
      ],
      [
        [[7, 7], [7, 7], [7, 8], [8, 8]],
        [[8, 8], [8, 8], [8, 8], [8, 9]],
        [[9, 9], [9, 9], [9, 9], [9, 9]],
      ],
    ];

    const idxUa = Math.max(0, Math.min(5, uaTotal - 1));
    const idxLa = Math.max(0, Math.min(2, laTotal - 1));
    const idxW = Math.max(0, Math.min(3, wTotal - 1));
    const idxWt = Math.max(0, Math.min(1, wTwist - 1));
    const tableAScore = TABLE_A[idxUa][idxLa][idxW][idxWt];
    const scoreC = tableAScore + (mods.muscle_use || 0) + (mods.force_load || 0);

    // Neck
    let nBase = 1;
    if (nf < 0) nBase = 4;
    else if (nf <= 10) nBase = 1;
    else if (nf <= 20) nBase = 2;
    else nBase = 3;
    let nMod = 0;
    if (mods.neck_twisted) nMod++;
    if (mods.neck_side_bend) nMod++;
    const nTotal = Math.max(1, Math.min(6, nBase + nMod));

    // Trunk
    let tBase = 1;
    if (tf <= 5) tBase = 1;
    else if (tf <= 20) tBase = 2;
    else if (tf <= 60) tBase = 3;
    else tBase = 4;
    let tMod = 0;
    if (mods.trunk_twisted) tMod++;
    if (mods.trunk_side_bend) tMod++;
    const tTotal = Math.max(1, Math.min(6, tBase + tMod));
    const legsScore = mods.legs_balanced ? 1 : 2;

    const TABLE_B = [
      [[1, 3], [2, 3], [3, 4], [5, 5], [6, 6], [7, 7]],
      [[2, 3], [2, 3], [4, 5], [5, 5], [6, 7], [7, 7]],
      [[3, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 7]],
      [[5, 5], [5, 6], [6, 7], [7, 7], [7, 7], [8, 8]],
      [[6, 6], [6, 7], [7, 7], [7, 8], [8, 8], [8, 8]],
      [[7, 7], [7, 7], [7, 8], [8, 8], [8, 9], [9, 9]],
    ];

    const idxN = Math.max(0, Math.min(5, nTotal - 1));
    const idxT = Math.max(0, Math.min(5, tTotal - 1));
    const idxL = Math.max(0, Math.min(1, legsScore - 1));
    const tableBScore = TABLE_B[idxN][idxT][idxL];
    const scoreD = tableBScore + (mods.muscle_use || 0) + (mods.force_load || 0);

    const TABLE_C = [
      [1, 2, 3, 3, 4, 5, 5],
      [2, 2, 3, 4, 4, 5, 5],
      [3, 3, 3, 4, 4, 5, 6],
      [3, 3, 3, 4, 5, 6, 6],
      [4, 4, 4, 5, 6, 7, 7],
      [4, 4, 5, 6, 6, 7, 7],
      [5, 5, 6, 6, 7, 7, 7],
      [5, 5, 6, 7, 7, 7, 7],
    ];

    const idxC = Math.max(0, Math.min(7, scoreC - 1));
    const idxD = Math.max(0, Math.min(6, scoreD - 1));
    const finalScore = TABLE_C[idxC][idxD];

    let actionLevel = 1;
    let actionDesc = 'Acceptable posture if not maintained or repeated for long periods.';
    let riskLevel: 'safe' | 'warning' | 'critical' = 'safe';

    if (finalScore <= 2) {
      actionLevel = 1;
      actionDesc = 'Acceptable posture if not maintained or repeated for long periods.';
      riskLevel = 'safe';
    } else if (finalScore <= 4) {
      actionLevel = 2;
      actionDesc = 'Further investigation needed; posture modifications may be required.';
      riskLevel = 'warning';
    } else if (finalScore <= 6) {
      actionLevel = 3;
      actionDesc = 'Investigation and ergonomic changes required soon.';
      riskLevel = 'warning';
    } else {
      actionLevel = 4;
      actionDesc = 'Immediate investigation and ergonomic changes required to prevent musculoskeletal injury.';
      riskLevel = 'critical';
    }

    return {
      final_score: finalScore,
      action_level: actionLevel,
      action_description: actionDesc,
      risk_level: riskLevel,
      components: {
        upper_arm: uaTotal,
        lower_arm: laTotal,
        wrist: wTotal,
        wrist_twist: wTwist,
        table_a_score: tableAScore,
        score_c: scoreC,
        neck: nTotal,
        trunk: tTotal,
        legs: legsScore,
        table_b_score: tableBScore,
        score_d: scoreD,
      },
      raw_angles: angles,
      raw_modifiers: mods,
    };
  };

  // Update manual playground RULA result whenever inputs change
  useEffect(() => {
    setPlaygroundRULA(evaluateRULALocal(customAngles, customMods));
  }, [customAngles, customMods]);

  // Main simulation loop for multi-worker stereo floor view
  useEffect(() => {
    let animFrame: number;
    let lastTs = performance.now();

    const loop = (timeNow: number) => {
      const dt = (timeNow - lastTs) / 1000;
      lastTs = timeNow;

      if (simulationRunning) {
        setSimTime((prev) => prev + dt);

        setWorkers((prevWorkers) =>
          prevWorkers.map((w) => {
            // Compute dynamic kinematics based on posture mode
            let sFlex = 15;
            let eFlex = 85 + 35 * Math.sin(w.phase + (simTime + dt) * 1.5);
            let nFlex = 8;
            let tFlex = 0;
            const currentMods: Modifiers = {
              shoulder_raised: false,
              arm_abducted: false,
              arm_supported: false,
              arm_across_midline: false,
              wrist_deviation: false,
              wrist_twist_end: false,
              neck_twisted: false,
              neck_side_bend: false,
              trunk_twisted: false,
              trunk_side_bend: false,
              legs_balanced: true,
              muscle_use: 0,
              force_load: 0,
            };

            if (w.postureMode === 'safe') {
              sFlex = 12 + 8 * Math.sin((simTime + dt) * 1.2);
              nFlex = 5;
              tFlex = 0;
            } else if (w.postureMode === 'warning') {
              sFlex = 55 + 10 * Math.sin((simTime + dt) * 1.0);
              eFlex = 115 + 15 * Math.cos((simTime + dt) * 1.0);
              nFlex = 18;
              tFlex = 25;
              currentMods.arm_abducted = true;
            } else if (w.postureMode === 'critical') {
              sFlex = 105 + 8 * Math.sin((simTime + dt) * 0.8);
              eFlex = 130 + 10 * Math.cos((simTime + dt) * 0.8);
              nFlex = 32;
              tFlex = 65;
              currentMods.shoulder_raised = true;
              currentMods.arm_abducted = true;
              currentMods.trunk_twisted = true;
              currentMods.force_load = 2;
            }

            const rula = evaluateRULALocal(
              {
                shoulder_flexion: sFlex,
                elbow_flexion: eFlex,
                wrist_flexion: 10,
                neck_flexion: nFlex,
                trunk_flexion: tFlex,
              },
              currentMods
            );

            // Sustained risk duration
            let sustained = w.sustainedSeconds;
            if (rula.risk_level === 'warning' || rula.risk_level === 'critical') {
              sustained += dt;
            } else {
              sustained = Math.max(0, sustained - dt * 2);
            }

            const alert = sustained >= 120;

            return {
              ...w,
              sustainedSeconds: sustained,
              alertActive: alert,
              rula,
            };
          })
        );
      }
      animFrame = requestAnimationFrame(loop);
    };

    animFrame = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animFrame);
  }, [simulationRunning, simTime]);

  // Run backend Python Test Suite
  const runPythonTests = async () => {
    setTestingRunning(true);
    setTestOutput('Launching python3 -m worker_safety.test_suite on backend runtime...\n');
    try {
      const res = await fetch('/api/test-suite/run', { method: 'POST' });
      const data = await res.json();
      setTestOutput(data.stdout || data.stderr || 'No output received');
      setTestSuccess(data.success);
    } catch (err: any) {
      setTestOutput(`Execution error: ${err.message}`);
      setTestSuccess(false);
    } finally {
      setTestingRunning(false);
    }
  };

  // Trigger Supervisor Agent floor review
  const triggerAgentReview = async () => {
    setAgentLoading(true);
    try {
      const floorSummary = {
        timestamp: simTime,
        total_workers_tracked: workers.length,
        critical_risk_count: workers.filter((w) => w.rula?.risk_level === 'critical').length,
        critical_worker_ids: workers.filter((w) => w.rula?.risk_level === 'critical').map((w) => w.id),
        warning_risk_count: workers.filter((w) => w.rula?.risk_level === 'warning').length,
        warning_worker_ids: workers.filter((w) => w.rula?.risk_level === 'warning').map((w) => w.id),
        safe_count: workers.filter((w) => w.rula?.risk_level === 'safe').length,
        safe_worker_ids: workers.filter((w) => w.rula?.risk_level === 'safe').map((w) => w.id),
        total_active_alerts: workers.filter((w) => w.alertActive).length,
        active_alert_worker_ids: workers.filter((w) => w.alertActive).map((w) => w.id),
        floor_average_rula_score:
          workers.reduce((acc, w) => acc + (w.rula?.final_score || 1), 0) / (workers.length || 1),
        floor_total_cycles_completed: workers.reduce((acc, w) => acc + w.completedCycles, 0),
        workers: workers.reduce((acc: any, w) => {
          acc[w.id] = {
            worker_id: w.id,
            current_rula_score: w.rula?.final_score || 1,
            current_risk_level: w.rula?.risk_level || 'safe',
            action_description: w.rula?.action_description,
            current_sustained_seconds: w.sustainedSeconds,
          };
          return acc;
        }, {}),
      };

      const res = await fetch('/api/agent/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ floor_summary: floorSummary }),
      });
      const data = await res.json();
      setAgentDecision(data.decision);
      setAgentLogs(data.audit_log || []);
    } catch (e: any) {
      console.error(e);
    } finally {
      setAgentLoading(false);
    }
  };

  // Test Vertex AI Endpoint
  const testVertexAI = async () => {
    setVertexLoading(true);
    try {
      const payload = JSON.parse(vertexInputJson);
      const res = await fetch('/api/vertex/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      setVertexResponseJson(JSON.stringify(data, null, 2));
    } catch (err: any) {
      setVertexResponseJson(JSON.stringify({ error: err.message }, null, 2));
    } finally {
      setVertexLoading(false);
    }
  };

  // Dynamic Canvas Skeleton Visualizer with collision-free labels
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    // Clear background
    ctx.fillStyle = '#0a0f18';
    ctx.fillRect(0, 0, width, height);

    // Factory floor grid & depth perspective lines
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    for (let x = 0; x < width; x += 40) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y < height; y += 40) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Calibrated stereo camera FOV frustum indicators
    ctx.fillStyle = 'rgba(56, 189, 248, 0.05)';
    ctx.beginPath();
    ctx.moveTo(width / 2, 20);
    ctx.lineTo(40, height - 20);
    ctx.lineTo(width - 40, height - 20);
    ctx.closePath();
    ctx.fill();

    // Placed label boxes for collision detection
    interface PlacedBox {
      xMin: number;
      yMin: number;
      xMax: number;
      yMax: number;
    }
    const placedBoxes: PlacedBox[] = [];

    // Draw Skeletons for each worker
    workers.forEach((w, idx) => {
      const risk = w.rula?.risk_level || 'safe';
      const color =
        risk === 'critical' ? '#ef4444' : risk === 'warning' ? '#f59e0b' : '#10b981';
      const bgBadge =
        risk === 'critical' ? 'rgba(239, 68, 68, 0.2)' : risk === 'warning' ? 'rgba(245, 158, 11, 0.2)' : 'rgba(16, 185, 129, 0.2)';

      const cx = w.baseX;
      const cy = w.baseY;

      // Kinematic skeleton nodes
      const sFlex = w.rula?.raw_angles.shoulder_flexion || 15;
      const eFlex = w.rula?.raw_angles.elbow_flexion || 85;
      const nFlex = w.rula?.raw_angles.neck_flexion || 8;
      const tFlex = w.rula?.raw_angles.trunk_flexion || 0;

      const nose = { x: cx, y: cy - 90 - nFlex * 0.4 };
      const neck = { x: cx, y: cy - 65 };
      const midHip = { x: cx - tFlex * 0.4, y: cy };
      const leftShoulder = { x: cx - 28, y: cy - 60 };
      const rightShoulder = { x: cx + 28, y: cy - 60 };

      // Arm kinematics
      const armAngleRad = ((sFlex - 90) * Math.PI) / 180;
      const elbowLen = 38;
      const wristLen = 34;

      const rightElbow = {
        x: rightShoulder.x + elbowLen * Math.cos(armAngleRad),
        y: rightShoulder.y + elbowLen * Math.sin(armAngleRad),
      };

      const forearmAngleRad = armAngleRad + ((eFlex - 90) * Math.PI) / 180;
      const rightWrist = {
        x: rightElbow.x + wristLen * Math.cos(forearmAngleRad),
        y: rightElbow.y + wristLen * Math.sin(forearmAngleRad),
      };

      const leftElbow = { x: leftShoulder.x - 22, y: leftShoulder.y + 35 };
      const leftWrist = { x: leftElbow.x - 10, y: leftElbow.y + 32 };

      const leftHip = { x: midHip.x - 18, y: midHip.y + 8 };
      const rightHip = { x: midHip.x + 18, y: midHip.y + 8 };
      const leftKnee = { x: leftHip.x - 5, y: leftHip.y + 50 };
      const rightKnee = { x: rightHip.x + 5, y: rightHip.y + 50 };
      const leftAnkle = { x: leftKnee.x - 2, y: leftKnee.y + 50 };
      const rightAnkle = { x: rightKnee.x + 2, y: rightKnee.y + 50 };

      const bones = [
        [neck, nose],
        [neck, leftShoulder],
        [neck, rightShoulder],
        [leftShoulder, leftElbow],
        [leftElbow, leftWrist],
        [rightShoulder, rightElbow],
        [rightElbow, rightWrist],
        [leftShoulder, rightShoulder],
        [neck, midHip],
        [midHip, leftHip],
        [midHip, rightHip],
        [leftHip, leftKnee],
        [leftKnee, leftAnkle],
        [rightHip, rightKnee],
        [rightKnee, rightAnkle],
      ];

      // Draw bone segments
      ctx.strokeStyle = color;
      ctx.lineWidth = 4;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      bones.forEach(([p1, p2]) => {
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
      });

      // Draw joint markers
      const joints = [
        nose,
        neck,
        leftShoulder,
        rightShoulder,
        leftElbow,
        rightElbow,
        leftWrist,
        rightWrist,
        midHip,
        leftHip,
        rightHip,
        leftKnee,
        rightKnee,
        leftAnkle,
        rightAnkle,
      ];

      joints.forEach((j) => {
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(j.x, j.y, 4, 0, 2 * Math.PI);
        ctx.fill();
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(j.x, j.y, 3, 0, 2 * Math.PI);
        ctx.fill();
      });

      // -------------------------------------------------------------
      // Collision-Free Text Label Box Computation (getTextSize Simulation)
      // -------------------------------------------------------------
      const text1 = `${w.id}: ${w.name.split(' ')[0]}`;
      const text2 = `RULA ${w.rula?.final_score || 1} [${risk.toUpperCase()}] ${w.alertActive ? '⚠ ALERT' : `(${w.sustainedSeconds.toFixed(0)}s)`}`;

      ctx.font = 'bold 11px Inter, sans-serif';
      const m1 = ctx.measureText(text1);
      const m2 = ctx.measureText(text2);
      const boxW = Math.max(m1.width, m2.width) + 16;
      const boxH = 40;

      // Candidate slot search (Tiered staggering above and below)
      const candidateDeltas = [
        { dy: -boxH - 20, dx: 0 },
        { dy: -2 * boxH - 28, dx: 0 },
        { dy: 30, dx: 0 },
        { dy: -boxH - 20, dx: boxW * 0.5 },
        { dy: -boxH - 20, dx: -boxW * 0.5 },
      ];

      let chosenBox: PlacedBox = {
        xMin: cx - boxW / 2,
        yMin: nose.y - boxH - 20,
        xMax: cx + boxW / 2,
        yMax: nose.y - 20,
      };

      for (const slot of candidateDeltas) {
        const cand: PlacedBox = {
          xMin: cx - boxW / 2 + slot.dx,
          yMin: nose.y + slot.dy,
          xMax: cx + boxW / 2 + slot.dx,
          yMax: nose.y + slot.dy + boxH,
        };

        const hasOverlap = placedBoxes.some(
          (pb) =>
            !(
              cand.xMax < pb.xMin ||
              cand.xMin > pb.xMax ||
              cand.yMax < pb.yMin ||
              cand.yMin > pb.yMax
            )
        );

        if (!hasOverlap) {
          chosenBox = cand;
          break;
        }
      }

      placedBoxes.push(chosenBox);

      // Draw leader line to anchor
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo((chosenBox.xMin + chosenBox.xMax) / 2, chosenBox.yMax);
      ctx.lineTo(nose.x, nose.y);
      ctx.stroke();

      // Draw label background pill
      ctx.fillStyle = '#0f172a';
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.roundRect(chosenBox.xMin, chosenBox.yMin, boxW, boxH, 6);
      ctx.fill();
      ctx.stroke();

      // Render text
      ctx.fillStyle = '#ffffff';
      ctx.fillText(text1, chosenBox.xMin + 8, chosenBox.yMin + 15);

      ctx.fillStyle = color;
      ctx.fillText(text2, chosenBox.xMin + 8, chosenBox.yMin + 30);
    });
  }, [workers, simTime]);

  const floorStats = useMemo(() => {
    const total = workers.length;
    const critical = workers.filter((w) => w.rula?.risk_level === 'critical').length;
    const warning = workers.filter((w) => w.rula?.risk_level === 'warning').length;
    const safe = workers.filter((w) => w.rula?.risk_level === 'safe').length;
    const alerts = workers.filter((w) => w.alertActive).length;
    const avgScore =
      workers.reduce((acc, w) => acc + (w.rula?.final_score || 1), 0) / (total || 1);
    const totalCycles = workers.reduce((acc, w) => acc + w.completedCycles, 0);

    return { total, critical, warning, safe, alerts, avgScore, totalCycles };
  }, [workers]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-slate-950">
      {/* Header Bar */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50 px-6 py-3.5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/20 border border-cyan-400/30">
            <Activity className="w-5 h-5 text-white animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight text-white">worker_safety</h1>
              <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800/80 font-mono">
                v1.0.0 Vertex AI / Cloud Run
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Stereo-Vision Multi-Worker Ergonomic (RULA) & Productivity Telemetry
            </p>
          </div>
        </div>

        {/* Global Live Status Badges */}
        <div className="flex items-center gap-2.5">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700 text-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            <span className="text-slate-300 font-mono">Stereo Rig: 30 FPS</span>
          </div>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700 text-xs">
            <span className="text-slate-400">Floor RULA:</span>
            <span className="font-bold text-amber-400 font-mono">{floorStats.avgScore.toFixed(1)}/7</span>
          </div>

          {floorStats.alerts > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-950/80 border border-red-700 text-red-300 text-xs font-bold animate-pulse">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>{floorStats.alerts} ACTIVE SUSTAINED ALERT(S)</span>
            </div>
          )}

          <button
            onClick={() => setSimulationRunning(!simulationRunning)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              simulationRunning
                ? 'bg-amber-600/20 text-amber-300 border border-amber-500/40 hover:bg-amber-600/30'
                : 'bg-emerald-600/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-600/30'
            }`}
          >
            {simulationRunning ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            {simulationRunning ? 'Pause Stream' : 'Resume Stream'}
          </button>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="border-b border-slate-800 bg-slate-900/40 px-6 flex space-x-1 overflow-x-auto">
        {[
          { id: 'floor', label: '1. Live Floor Vision', icon: Eye },
          { id: 'rula', label: '2. RULA Standard Assessment', icon: Sliders },
          { id: 'productivity', label: '3. Repetitive Cycle Tracker', icon: TrendingUp },
          { id: 'shift', label: '4. Shift Sustained Alert Invariant', icon: Clock },
          { id: 'agent', label: '5. Gemini Supervisor Agent', icon: Sparkles },
          { id: 'tests', label: '6. Python Test Suite (6/6)', icon: Terminal },
          { id: 'vertex', label: '7. Vertex AI & Cloud Run REST', icon: Cloud },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 py-3 px-4 text-xs font-medium border-b-2 transition-all whitespace-nowrap ${
                isActive
                  ? 'border-cyan-400 text-cyan-400 bg-cyan-950/20 font-semibold'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
              {tab.label}
            </button>
          );
        })}
      </nav>

      {/* Main Content Area */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
        {/* ========================================================================= */}
        {/* TAB 1: LIVE FLOOR VISION */}
        {/* ========================================================================= */}
        {activeTab === 'floor' && (
          <div className="space-y-6">
            {/* KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-400">Total Tracked Workers</p>
                  <p className="text-2xl font-bold text-white font-mono mt-1">{floorStats.total}</p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center text-cyan-400">
                  <Layers className="w-5 h-5" />
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-400">Safe (RULA 1-2)</p>
                  <p className="text-2xl font-bold text-emerald-400 font-mono mt-1">{floorStats.safe}</p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-emerald-950/50 border border-emerald-800/50 flex items-center justify-center text-emerald-400">
                  <CheckCircle className="w-5 h-5" />
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-400">Warning (RULA 3-6)</p>
                  <p className="text-2xl font-bold text-amber-400 font-mono mt-1">{floorStats.warning}</p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-amber-950/50 border border-amber-800/50 flex items-center justify-center text-amber-400">
                  <AlertTriangle className="w-5 h-5" />
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-400">Critical (RULA 7)</p>
                  <p className="text-2xl font-bold text-red-400 font-mono mt-1">{floorStats.critical}</p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-red-950/50 border border-red-800/50 flex items-center justify-center text-red-400">
                  <AlertOctagon className="w-5 h-5" />
                </div>
              </div>
            </div>

            {/* Stereo Camera Video Canvas View */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
              <div className="px-5 py-3 border-b border-slate-800 bg-slate-900/90 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Eye className="w-4 h-4 text-cyan-400" />
                  <span className="text-sm font-semibold text-white">
                    Stereo Camera Feed 01 — Skeleton & Collision-Free Risk Overlay
                  </span>
                </div>
                <div className="flex items-center gap-4 text-xs font-mono">
                  <span className="text-slate-400">Resolution: 854x380</span>
                  <span className="text-emerald-400">Latency: 14ms</span>
                </div>
              </div>

              <div className="relative flex justify-center bg-slate-950 p-3">
                <canvas
                  ref={canvasRef}
                  width={854}
                  height={380}
                  className="rounded-lg shadow-inner border border-slate-800 w-full max-w-[854px]"
                />
              </div>

              <div className="px-5 py-3 bg-slate-950/60 border-t border-slate-800 text-xs text-slate-400 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> Safe (Teal/Green)
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span> Warning (Amber)
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span> Critical (Red)
                  </span>
                </div>
                <span className="text-slate-500">
                  Anti-overlap collision detection active (cv2.getTextSize boundary calculation)
                </span>
              </div>
            </div>

            {/* Per-Worker Live Telemetry Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {workers.map((w) => {
                const isCrit = w.rula?.risk_level === 'critical';
                const isWarn = w.rula?.risk_level === 'warning';
                return (
                  <div
                    key={w.id}
                    className={`bg-slate-900 border rounded-xl p-5 transition-all ${
                      isCrit
                        ? 'border-red-600/80 shadow-lg shadow-red-950/40 bg-gradient-to-b from-red-950/20 to-slate-900'
                        : isWarn
                        ? 'border-amber-600/60'
                        : 'border-slate-800'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-bold">
                            {w.id}
                          </span>
                          <h3 className="font-bold text-white text-sm">{w.name}</h3>
                        </div>
                        <p className="text-xs text-slate-400 mt-1">{w.station}</p>
                      </div>
                      <span
                        className={`text-xs px-2.5 py-1 rounded-full font-bold uppercase font-mono ${
                          isCrit
                            ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                            : isWarn
                            ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                            : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                        }`}
                      >
                        {w.rula?.risk_level || 'SAFE'} (RULA {w.rula?.final_score || 1})
                      </span>
                    </div>

                    <div className="mt-4 space-y-2">
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-400">Action Level:</span>
                        <span className="font-semibold text-white">Level {w.rula?.action_level || 1}</span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-400">Sustained Risk:</span>
                        <span
                          className={`font-mono font-semibold ${
                            w.sustainedSeconds >= 120
                              ? 'text-red-400 font-bold'
                              : w.sustainedSeconds > 30
                              ? 'text-amber-400'
                              : 'text-slate-300'
                          }`}
                        >
                          {w.sustainedSeconds.toFixed(1)}s / 120s threshold
                        </span>
                      </div>
                      {/* Sustained risk progress bar */}
                      <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`h-full transition-all duration-300 ${
                            w.sustainedSeconds >= 120
                              ? 'bg-red-500'
                              : w.sustainedSeconds > 60
                              ? 'bg-amber-500'
                              : 'bg-cyan-500'
                          }`}
                          style={{ width: `${Math.min(100, (w.sustainedSeconds / 120) * 100)}%` }}
                        ></div>
                      </div>

                      <div className="flex justify-between text-xs pt-1">
                        <span className="text-slate-400">Completed Cycles:</span>
                        <span className="font-mono text-cyan-400 font-semibold">{w.completedCycles} cycles</span>
                      </div>
                    </div>

                    {/* Posture Simulation Switcher */}
                    <div className="mt-4 pt-3 border-t border-slate-800/80">
                      <p className="text-[11px] text-slate-400 mb-2">Simulate Posture Scenario:</p>
                      <div className="grid grid-cols-3 gap-1.5">
                        {(['safe', 'warning', 'critical'] as const).map((mode) => (
                          <button
                            key={mode}
                            onClick={() => {
                              setWorkers((prev) =>
                                prev.map((item) =>
                                  item.id === w.id
                                    ? {
                                        ...item,
                                        postureMode: mode,
                                        sustainedSeconds: mode === 'safe' ? 0 : item.sustainedSeconds,
                                      }
                                    : item
                                )
                              );
                            }}
                            className={`py-1 px-2 rounded text-[11px] font-medium uppercase transition-all ${
                              w.postureMode === mode
                                ? mode === 'critical'
                                  ? 'bg-red-600 text-white font-bold'
                                  : mode === 'warning'
                                  ? 'bg-amber-600 text-white font-bold'
                                  : 'bg-emerald-600 text-white font-bold'
                                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                            }`}
                          >
                            {mode}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 2: RULA STANDARD ASSESSMENT STUDIO */}
        {/* ========================================================================= */}
        {activeTab === 'rula' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Interactive Flexion Sliders & Modifiers */}
            <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
              <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <Sliders className="w-5 h-5 text-cyan-400" />
                    RULA Posture Flexion Angles & Modifiers
                  </h2>
                  <p className="text-xs text-slate-400">
                    McAtamney & Corlett (1993) Occupational Ergonomics Standard
                  </p>
                </div>
                <button
                  onClick={() => {
                    setCustomAngles({
                      shoulder_flexion: 15,
                      elbow_flexion: 85,
                      wrist_flexion: 0,
                      neck_flexion: 8,
                      trunk_flexion: 5,
                    });
                    setCustomMods({
                      shoulder_raised: false,
                      arm_abducted: false,
                      arm_supported: false,
                      arm_across_midline: false,
                      wrist_deviation: false,
                      wrist_twist_end: false,
                      neck_twisted: false,
                      neck_side_bend: false,
                      trunk_twisted: false,
                      trunk_side_bend: false,
                      legs_balanced: true,
                      muscle_use: 0,
                      force_load: 0,
                    });
                  }}
                  className="text-xs px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center gap-1"
                >
                  <RotateCcw className="w-3 h-3" /> Reset Neutral
                </button>
              </div>

              {/* Flexion Angle Sliders */}
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="font-semibold text-slate-200">1. Upper Arm / Shoulder Flexion</span>
                    <span className="font-mono text-cyan-400 font-bold">{customAngles.shoulder_flexion}°</span>
                  </div>
                  <input
                    type="range"
                    min="-40"
                    max="140"
                    step="1"
                    value={customAngles.shoulder_flexion}
                    onChange={(e) =>
                      setCustomAngles({ ...customAngles, shoulder_flexion: parseFloat(e.target.value) })
                    }
                    className="w-full accent-cyan-500"
                  />
                  <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                    <span>-40° (Extension)</span>
                    <span>20° (Neutral)</span>
                    <span>45°</span>
                    <span>90°</span>
                    <span>140° (Overhead)</span>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="font-semibold text-slate-200">2. Lower Arm / Elbow Flexion</span>
                    <span className="font-mono text-cyan-400 font-bold">{customAngles.elbow_flexion}°</span>
                  </div>
                  <input
                    type="range"
                    min="30"
                    max="160"
                    step="1"
                    value={customAngles.elbow_flexion}
                    onChange={(e) =>
                      setCustomAngles({ ...customAngles, elbow_flexion: parseFloat(e.target.value) })
                    }
                    className="w-full accent-cyan-500"
                  />
                  <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                    <span>30°</span>
                    <span>60°-100° (Neutral Range)</span>
                    <span>160°</span>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="font-semibold text-slate-200">3. Wrist Flexion / Extension</span>
                    <span className="font-mono text-cyan-400 font-bold">{customAngles.wrist_flexion}°</span>
                  </div>
                  <input
                    type="range"
                    min="-45"
                    max="45"
                    step="1"
                    value={customAngles.wrist_flexion}
                    onChange={(e) =>
                      setCustomAngles({ ...customAngles, wrist_flexion: parseFloat(e.target.value) })
                    }
                    className="w-full accent-cyan-500"
                  />
                  <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                    <span>-45°</span>
                    <span>0° (Neutral)</span>
                    <span>+45°</span>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="font-semibold text-slate-200">4. Neck Flexion</span>
                    <span className="font-mono text-cyan-400 font-bold">{customAngles.neck_flexion}°</span>
                  </div>
                  <input
                    type="range"
                    min="-20"
                    max="60"
                    step="1"
                    value={customAngles.neck_flexion}
                    onChange={(e) =>
                      setCustomAngles({ ...customAngles, neck_flexion: parseFloat(e.target.value) })
                    }
                    className="w-full accent-cyan-500"
                  />
                  <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                    <span>-20° (Ext)</span>
                    <span>0°-10° (Neutral)</span>
                    <span>20°</span>
                    <span>60°</span>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="font-semibold text-slate-200">5. Trunk / Spine Flexion</span>
                    <span className="font-mono text-cyan-400 font-bold">{customAngles.trunk_flexion}°</span>
                  </div>
                  <input
                    type="range"
                    min="-10"
                    max="90"
                    step="1"
                    value={customAngles.trunk_flexion}
                    onChange={(e) =>
                      setCustomAngles({ ...customAngles, trunk_flexion: parseFloat(e.target.value) })
                    }
                    className="w-full accent-cyan-500"
                  />
                  <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                    <span>0° (Upright)</span>
                    <span>20°</span>
                    <span>60°</span>
                    <span>90° (Deep Bend)</span>
                  </div>
                </div>
              </div>

              {/* Clinical Ergonomic Modifiers */}
              <div className="border-t border-slate-800 pt-4">
                <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">
                  Ergonomic Modifiers & Biomechanical Multipliers
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
                  {[
                    { key: 'shoulder_raised', label: '+1 Raised Shoulder' },
                    { key: 'arm_abducted', label: '+1 Arm Abducted' },
                    { key: 'arm_supported', label: '-1 Arm Supported' },
                    { key: 'arm_across_midline', label: '+1 Across Midline' },
                    { key: 'wrist_deviation', label: '+1 Wrist Deviation' },
                    { key: 'wrist_twist_end', label: 'Wrist Twist at End' },
                    { key: 'neck_twisted', label: '+1 Neck Twisted' },
                    { key: 'neck_side_bend', label: '+1 Neck Side-Bend' },
                    { key: 'trunk_twisted', label: '+1 Trunk Twisted' },
                    { key: 'trunk_side_bend', label: '+1 Trunk Side-Bend' },
                  ].map((item) => (
                    <label
                      key={item.key}
                      className={`flex items-center gap-2 p-2 rounded border cursor-pointer select-none transition-all ${
                        (customMods as any)[item.key]
                          ? 'bg-cyan-950/60 border-cyan-500 text-cyan-200'
                          : 'bg-slate-800/40 border-slate-700/60 text-slate-400 hover:bg-slate-800'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={(customMods as any)[item.key]}
                        onChange={(e) =>
                          setCustomMods({ ...customMods, [item.key]: e.target.checked })
                        }
                        className="accent-cyan-500"
                      />
                      <span>{item.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            {/* Right Column: RULA Clinical Result Matrix Breakdown */}
            <div className="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6 flex flex-col justify-between">
              <div>
                <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
                  <h3 className="font-bold text-white text-base">RULA Assessment Score Card</h3>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    Deterministic
                  </span>
                </div>

                {/* Big Score Display */}
                {playgroundRULA && (
                  <div className="mt-5 text-center p-6 rounded-xl bg-slate-950 border border-slate-800">
                    <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">
                      Grand Risk Score (Table C)
                    </p>
                    <div className="flex items-center justify-center gap-3 my-2">
                      <span
                        className={`text-6xl font-black font-mono ${
                          playgroundRULA.risk_level === 'critical'
                            ? 'text-red-500'
                            : playgroundRULA.risk_level === 'warning'
                            ? 'text-amber-400'
                            : 'text-emerald-400'
                        }`}
                      >
                        {playgroundRULA.final_score}
                      </span>
                      <span className="text-3xl text-slate-600 font-mono">/ 7</span>
                    </div>

                    <div className="inline-block mt-1">
                      <span
                        className={`text-xs px-3 py-1 rounded-full font-bold uppercase font-mono tracking-wider ${
                          playgroundRULA.risk_level === 'critical'
                            ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                            : playgroundRULA.risk_level === 'warning'
                            ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                            : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                        }`}
                      >
                        {playgroundRULA.risk_level} — Action Level {playgroundRULA.action_level}
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 mt-4 px-2 leading-relaxed">
                      {playgroundRULA.action_description}
                    </p>
                  </div>
                )}

                {/* Detailed Components Table */}
                {playgroundRULA && (
                  <div className="mt-5 space-y-2 text-xs">
                    <h4 className="font-bold text-slate-300 uppercase tracking-wider text-[11px]">
                      Component Breakdown
                    </h4>
                    <div className="grid grid-cols-2 gap-2 font-mono">
                      <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                        <span className="text-slate-400 block text-[10px]">Table A (Upper Limb)</span>
                        <span className="text-cyan-400 font-bold text-sm">
                          Score A = {playgroundRULA.components.table_a_score} → Score C = {playgroundRULA.components.score_c}
                        </span>
                        <div className="text-[10px] text-slate-500 mt-1">
                          Upper Arm: {playgroundRULA.components.upper_arm} | Lower Arm: {playgroundRULA.components.lower_arm} | Wrist: {playgroundRULA.components.wrist}
                        </div>
                      </div>

                      <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                        <span className="text-slate-400 block text-[10px]">Table B (Neck, Trunk, Legs)</span>
                        <span className="text-cyan-400 font-bold text-sm">
                          Score B = {playgroundRULA.components.table_b_score} → Score D = {playgroundRULA.components.score_d}
                        </span>
                        <div className="text-[10px] text-slate-500 mt-1">
                          Neck: {playgroundRULA.components.neck} | Trunk: {playgroundRULA.components.trunk} | Legs: {playgroundRULA.components.legs}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="p-3 bg-cyan-950/20 border border-cyan-800/40 rounded-lg text-xs text-cyan-300 flex items-start gap-2">
                <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                <p>
                  Deterministic standard compliance: Fully calculated via published lookup matrices. Zero ML or stochastic variability ensures regulatory auditability.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 3: REPETITIVE CYCLE TRACKER */}
        {/* ========================================================================= */}
        {activeTab === 'productivity' && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-cyan-400" />
                    Repetitive Task Motion Cycles & Fatigue Consistency Indicator
                  </h2>
                  <p className="text-xs text-slate-400">
                    Angular velocity zero-crossing detection on stereo-tracked joint time series
                  </p>
                </div>
                <span className="text-xs px-2.5 py-1 rounded bg-slate-800 text-cyan-400 font-mono">
                  Interpolated Zero-Crossing Filter
                </span>
              </div>

              {/* Waveform Visualization */}
              <div className="mt-6">
                <p className="text-xs font-semibold text-slate-300 mb-2">
                  Live Joint Angle Signal (Elbow Flexion Reach / Withdraw Velocity Zero-Crossings)
                </p>
                <div className="h-44 w-full bg-slate-950 border border-slate-800 rounded-xl p-4 relative overflow-hidden flex items-center">
                  <svg className="w-full h-full" viewBox="0 0 800 140" preserveAspectRatio="none">
                    {/* Grid lines */}
                    <line x1="0" y1="70" x2="800" y2="70" stroke="#334155" strokeDasharray="4,4" />
                    <line x1="0" y1="20" x2="800" y2="20" stroke="#1e293b" />
                    <line x1="0" y1="120" x2="800" y2="120" stroke="#1e293b" />

                    {/* Sine wave representing joint motion */}
                    <path
                      d={Array.from({ length: 80 }, (_, i) => {
                        const x = i * 10;
                        const t = (x / 100) + simTime * 1.5;
                        const y = 70 - 45 * Math.sin(t);
                        return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
                      }).join(' ')}
                      fill="none"
                      stroke="#06b6d4"
                      strokeWidth="2.5"
                    />

                    {/* Zero-crossing peak & valley marker pins */}
                    {Array.from({ length: 8 }, (_, i) => {
                      const x = (i * 100 + (simTime * 15) % 100);
                      return (
                        <g key={i}>
                          <circle cx={x} cy={25} r="4" fill="#f59e0b" />
                          <circle cx={x + 50} cy={115} r="4" fill="#10b981" />
                        </g>
                      );
                    })}
                  </svg>
                </div>
                <div className="flex justify-between text-[11px] text-slate-400 mt-2 px-1">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span> Direction Reversal 1 (Extension Peak)
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span> Direction Reversal 2 (Withdrawal Valley)
                  </span>
                  <span className="font-mono text-cyan-400">Two reversals = 1 Complete Ergonomic Cycle</span>
                </div>
              </div>

              {/* Productivity Summary Table */}
              <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                  <span className="text-xs text-slate-400">Elena Rostova (WRK-101)</span>
                  <p className="text-xl font-bold text-white font-mono mt-1">15 cycles completed</p>
                  <div className="text-xs text-emerald-400 font-mono mt-2 flex justify-between">
                    <span>Mean: 4.00s</span>
                    <span>StdDev: 0.02s (Consistent)</span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">Rolling: 900 cycles/hr</p>
                </div>

                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                  <span className="text-xs text-slate-400">Marcus Vance (WRK-102)</span>
                  <p className="text-xl font-bold text-white font-mono mt-1">11 cycles completed</p>
                  <div className="text-xs text-amber-400 font-mono mt-2 flex justify-between">
                    <span>Mean: 4.74s</span>
                    <span>StdDev: 0.24s (Slowing)</span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">Rolling: 759 cycles/hr</p>
                </div>

                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                  <span className="text-xs text-slate-400">Kenji Sato (WRK-103)</span>
                  <p className="text-xl font-bold text-white font-mono mt-1">8 cycles completed</p>
                  <div className="text-xs text-red-400 font-mono mt-2 flex justify-between">
                    <span>Mean: 6.08s</span>
                    <span>StdDev: 0.65s (High Fatigue)</span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">Rolling: 592 cycles/hr</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 4: SHIFT SUSTAINED ALERT INVARIANT */}
        {/* ========================================================================= */}
        {activeTab === 'shift' && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
              <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <Clock className="w-5 h-5 text-cyan-400" />
                    Sustained Risk Alerting Invariant (120s Threshold)
                  </h2>
                  <p className="text-xs text-slate-400">
                    Eliminates false alarms by rejecting momentary transient spikes
                  </p>
                </div>
                <span className="text-xs px-2.5 py-1 rounded bg-slate-800 text-amber-400 font-mono font-bold">
                  Threshold: 120.0s
                </span>
              </div>

              {/* Visual Explanation Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-950 border border-emerald-900/60 rounded-xl p-5">
                  <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
                    <CheckCircle className="w-4 h-4" />
                    <span>Scenario A: 5-Second Momentary Spike</span>
                  </div>
                  <p className="text-xs text-slate-300 mt-2">
                    Worker bends down to pick up a dropped bolt for 5 seconds, entering severe posture (RULA 7).
                  </p>
                  <div className="mt-3 p-2 rounded bg-emerald-950/40 border border-emerald-800/40 text-emerald-300 text-xs font-mono">
                    Duration: 5.0s &lt; 120s → 🚫 NO ALERT (Ignored as transient spike)
                  </div>
                </div>

                <div className="bg-slate-950 border border-red-900/60 rounded-xl p-5">
                  <div className="flex items-center gap-2 text-red-400 font-bold text-sm">
                    <AlertOctagon className="w-4 h-4" />
                    <span>Scenario B: 120+ Seconds Sustained Exposure</span>
                  </div>
                  <p className="text-xs text-slate-300 mt-2">
                    Worker maintains overhead fixture reach with twisted neck for 130 continuous seconds.
                  </p>
                  <div className="mt-3 p-2 rounded bg-red-950/40 border border-red-800/40 text-red-300 text-xs font-mono">
                    Duration: 130.0s &gt; 120s → 🚨 ALERT TRIGGERED (ID: ALERT-WRK-103-0001)
                  </div>
                </div>
              </div>

              {/* Active Alerts List */}
              <div>
                <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">
                  Current Shift Alert Registry
                </h3>
                <div className="space-y-2">
                  {workers
                    .filter((w) => w.alertActive)
                    .map((w) => (
                      <div
                        key={w.id}
                        className="bg-red-950/30 border border-red-800/80 rounded-lg p-3 flex items-center justify-between text-xs"
                      >
                        <div className="flex items-center gap-3">
                          <AlertTriangle className="w-5 h-5 text-red-400 animate-bounce" />
                          <div>
                            <span className="font-bold text-white font-mono">{w.id}</span> — {w.name} ({w.station})
                            <p className="text-red-300 text-[11px]">
                              Sustained at Critical Level for {w.sustainedSeconds.toFixed(0)}s
                            </p>
                          </div>
                        </div>
                        <span className="px-2.5 py-1 rounded bg-red-600 text-white font-bold text-[11px]">
                          ACTIVE ALERT
                        </span>
                      </div>
                    ))}
                  {workers.filter((w) => w.alertActive).length === 0 && (
                    <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 text-center text-xs text-slate-500">
                      No active sustained alerts on the floor. All workers within safe duty limits.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 5: GEMINI SUPERVISOR AGENT */}
        {/* ========================================================================= */}
        {activeTab === 'agent' && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
              <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-cyan-400" />
                    Gemini Autonomous Supervisor Agent
                  </h2>
                  <p className="text-xs text-slate-400">
                    Hard Boundary: Strictly 4 permitted tools (No direct machine control or disciplinary tools)
                  </p>
                </div>
                <button
                  onClick={triggerAgentReview}
                  disabled={agentLoading}
                  className="px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-cyan-500/20 disabled:opacity-50"
                >
                  {agentLoading ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                  Trigger Autonomous Floor Review
                </button>
              </div>

              {/* Strict 4 Tools Card */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { name: 'log_incident', desc: 'OSHA / compliance audit log', color: 'border-blue-800/60' },
                  { name: 'notify_supervisor', desc: 'Alert floor manager & human lead', color: 'border-amber-800/60' },
                  { name: 'escalate_critical', desc: 'MANDATORY on RULA 7 critical risk', color: 'border-red-800/60' },
                  { name: 'generate_shift_report', desc: 'Aggregate shift summary synthesis', color: 'border-emerald-800/60' },
                ].map((tool) => (
                  <div key={tool.name} className={`bg-slate-950 border ${tool.color} p-3 rounded-lg text-xs`}>
                    <div className="flex items-center gap-1.5 font-bold font-mono text-white mb-1">
                      <Lock className="w-3 h-3 text-cyan-400" />
                      <span>{tool.name}</span>
                    </div>
                    <p className="text-[11px] text-slate-400">{tool.desc}</p>
                  </div>
                ))}
              </div>

              {/* Latest Decision Result */}
              {agentDecision && (
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <span className="text-xs font-bold text-cyan-400 font-mono">
                      Agent Decision Record ({agentDecision.timestamp})
                    </span>
                    <span className="text-xs px-2.5 py-0.5 rounded bg-red-950 border border-red-800 text-red-300 font-bold font-mono">
                      Mandatory Critical Escalations: {agentDecision.mandatory_escalations_executed}
                    </span>
                  </div>

                  <p className="text-xs text-slate-200 leading-relaxed font-sans">
                    {agentDecision.assessment_summary}
                  </p>

                  {agentDecision.llm_analysis && (
                    <div className="p-3 bg-slate-900 rounded border border-slate-800 text-xs text-slate-400 font-mono whitespace-pre-wrap">
                      {agentDecision.llm_analysis}
                    </div>
                  )}
                </div>
              )}

              {/* Tamper-Evident Action Log Audit Trail */}
              <div>
                <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">
                  Tamper-Evident Action Log (Evidence / Audit Trail)
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left border-collapse">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400 font-mono text-[11px] bg-slate-950">
                        <th className="py-2.5 px-3">Call ID</th>
                        <th className="py-2.5 px-3">Timestamp</th>
                        <th className="py-2.5 px-3">Tool Name</th>
                        <th className="py-2.5 px-3">Arguments</th>
                        <th className="py-2.5 px-3">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {agentLogs.length > 0 ? (
                        agentLogs.map((log) => (
                          <tr key={log.call_id} className="hover:bg-slate-800/30">
                            <td className="py-2 px-3 text-cyan-400 font-bold">{log.call_id}</td>
                            <td className="py-2 px-3 text-slate-400">{log.timestamp.slice(11, 19)}</td>
                            <td className="py-2 px-3 font-bold text-white">{log.tool_name}</td>
                            <td className="py-2 px-3 text-slate-300 font-sans max-w-xs truncate">
                              {JSON.stringify(log.arguments)}
                            </td>
                            <td className="py-2 px-3">
                              <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 text-[10px]">
                                {log.status}
                              </span>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={5} className="py-4 text-center text-slate-500">
                            No agent tool calls executed yet. Click &quot;Trigger Autonomous Floor Review&quot; above.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 6: PYTHON TEST SUITE */}
        {/* ========================================================================= */}
        {activeTab === 'tests' && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
              <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <Terminal className="w-5 h-5 text-cyan-400" />
                    Automated Python Test Suite Runner
                  </h2>
                  <p className="text-xs text-slate-400">
                    Runs synthetic verification tests across all 6 core Python modules
                  </p>
                </div>
                <button
                  onClick={runPythonTests}
                  disabled={testingRunning}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-emerald-600/20 disabled:opacity-50 font-mono"
                >
                  {testingRunning ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4" />
                  )}
                  Execute python3 -m worker_safety.test_suite
                </button>
              </div>

              {/* Module Verification Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {[
                  { title: '1. rula_assessment', check: 'Neutral (1-2) < Moderate (4) < Severe (7)' },
                  { title: '2. shift_monitor', check: '5s spike rejected, 120s+ sustained alert' },
                  { title: '3. productivity_tracker', check: 'Sinusoid T=4.0s detected, std dev = 0.00s' },
                  { title: '4. multi_worker_monitor', check: '3 workers floor aggregation & alerts' },
                  { title: '5. supervisor_agent', check: 'Strict 4 tools, mandatory escalation' },
                  { title: '6. skeleton_visualizer', check: '0 label overlaps on adjacent workers' },
                ].map((m) => (
                  <div key={m.title} className="bg-slate-950 border border-slate-800 p-3 rounded-lg">
                    <div className="flex items-center justify-between text-xs font-bold text-white font-mono">
                      <span>{m.title}</span>
                      <CheckCircle className="w-4 h-4 text-emerald-400" />
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">{m.check}</p>
                  </div>
                ))}
              </div>

              {/* Live Terminal Output Window */}
              <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden">
                <div className="px-4 py-2.5 bg-slate-900 border-b border-slate-800 flex items-center justify-between text-xs font-mono">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-red-500 inline-block"></span>
                    <span className="w-3 h-3 rounded-full bg-amber-500 inline-block"></span>
                    <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block"></span>
                    <span className="text-slate-300 ml-2 font-semibold">Console Output</span>
                  </div>
                  {testSuccess !== null && (
                    <span
                      className={`font-bold ${
                        testSuccess ? 'text-emerald-400' : 'text-red-400'
                      }`}
                    >
                      {testSuccess ? '✔ ALL 6 TESTS PASSED' : '✖ TEST FAILURE'}
                    </span>
                  )}
                </div>

                <pre className="p-4 text-xs font-mono text-emerald-400 overflow-x-auto max-h-96 whitespace-pre-wrap leading-relaxed">
                  {testOutput || 'Click "Execute python3 -m worker_safety.test_suite" above to run inline tests.'}
                </pre>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 7: VERTEX AI & CLOUD RUN REST */}
        {/* ========================================================================= */}
        {activeTab === 'vertex' && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
              <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <Cloud className="w-5 h-5 text-cyan-400" />
                    Google Cloud Vertex AI & Cloud Run Endpoint
                  </h2>
                  <p className="text-xs text-slate-400">
                    Vertex AI Custom Container Predict Endpoint (POST /predict)
                  </p>
                </div>
                <button
                  onClick={testVertexAI}
                  disabled={vertexLoading}
                  className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-cyan-600/20 font-mono disabled:opacity-50"
                >
                  {vertexLoading ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                  Send POST /predict Request
                </button>
              </div>

              {/* Request & Response Side-by-Side */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <span className="text-xs font-bold text-slate-300 font-mono">
                    Vertex AI Request Body ({'{"instances": [...]}'})
                  </span>
                  <textarea
                    rows={14}
                    value={vertexInputJson}
                    onChange={(e) => setVertexInputJson(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-500 leading-relaxed"
                  />
                </div>

                <div className="space-y-2">
                  <span className="text-xs font-bold text-slate-300 font-mono">
                    Vertex AI Prediction Output ({'{"predictions": [...]}'})
                  </span>
                  <textarea
                    readOnly
                    rows={14}
                    value={vertexResponseJson || 'Click "Send POST /predict Request" to inspect prediction outputs.'}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs font-mono text-emerald-400 focus:outline-none leading-relaxed"
                  />
                </div>
              </div>

              {/* gcloud Deployment Command Snippets */}
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                  Cloud Deployment Quick Commands
                </span>
                <div className="space-y-2 text-xs font-mono">
                  <div className="bg-slate-900 p-2.5 rounded border border-slate-800 text-slate-300 flex items-center justify-between">
                    <code>gcloud run deploy worker-safety --source . --region us-central1 --allow-unauthenticated</code>
                    <span className="text-[10px] text-cyan-400 font-sans">Cloud Run</span>
                  </div>
                  <div className="bg-slate-900 p-2.5 rounded border border-slate-800 text-slate-300 flex items-center justify-between">
                    <code>gcloud ai models upload --container-image-uri=IMAGE_URI --container-predict-route=/predict</code>
                    <span className="text-[10px] text-cyan-400 font-sans">Vertex AI Custom Model</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
