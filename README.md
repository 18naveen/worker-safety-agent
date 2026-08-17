# worker_safety

Continuous factory floor multi-worker ergonomic risk (RULA) and productivity monitoring system using stereo-vision-tracked human skeleton joint angles, deployable to **Google Cloud Run** and **Google Cloud Vertex AI Model Serving**.

---

## 🏛️ System Architecture

```
                                  [ Stereo Camera Rig ]
                                             │
                   3D/2D Joint Angles & Pixel Positions (30 FPS)
                                             │
                                             ▼
                             ┌───────────────────────────────┐
                             │    worker_safety Architecture │
                             └───────────────┬───────────────┘
                                             │
      ┌──────────────────────────────────────┼──────────────────────────────────────┐
      │                                      │                                      │
      ▼                                      ▼                                      ▼
┌───────────────────────────┐  ┌───────────────────────────┐  ┌───────────────────────────┐
│ 1. rula_assessment.py     │  │ 2. shift_monitor.py       │  │ 3. productivity_tracker.py│
│ McAtamney & Corlett 1993  │  │ Sustained Risk Invariant  │  │ Velocity Zero-Crossing    │
│ Tables A, B, C Determin-  │  │ (120s threshold, rejects  │  │ Repetitive Cycle Detection │
│ istic Scoring (1-7 Risk)  │  │ 5s momentary spikes)      │  │ Rate & Duration Std Dev   │
└─────────────┬─────────────┘  └─────────────┬─────────────┘  └─────────────┬─────────────┘
              │                              │                              │
              └──────────────────────────────┼──────────────────────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │ 4. multi_worker_monitor.py│
                               │ Per-Worker State Tracking │
                               │ Floor-Wide Risk Summary   │
                               └─────────────┬─────────────┘
                                             │
                      ┌──────────────────────┴──────────────────────┐
                      ▼                                             ▼
        ┌───────────────────────────┐                 ┌───────────────────────────┐
        │ 5. supervisor_agent.py    │                 │ 6. skeleton_visualizer.py │
        │ Gemini LLM Function Calls │                 │ OpenCV MediaPipe Overlay  │
        │ Strict 4 Safety Tools     │                 │ Dynamic Risk Color Coding │
        │ Mandatory Escalations     │                 │ Collision-Free Labels     │
        │ Audit Trail Action Log    │                 │ (getTextSize Staggering)  │
        └───────────────────────────┘                 └───────────────────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │ 7. main.py (FastAPI)      │
                               │ Vertex AI Custom Serve    │
                               │ Cloud Run REST Endpoints  │
                               └───────────────────────────┘
```

---

## 📦 Modules Overview

### 1. `rula_assessment.py`
- Implements the **Rapid Upper Limb Assessment (RULA)** occupational ergonomics standard (McAtamney & Corlett 1993).
- Evaluates Upper Arm, Lower Arm, Wrist, Wrist Twist, Neck, Trunk, Legs with clinical posture modifiers (abduction, shoulder raise, twist, lateral bending).
- Computes Posture Tables A, B, Muscle/Force loads, Scores C, D, and Table C Grand Score (1-7).
- Action Levels:
  - **1-2**: *Safe* (Acceptable posture)
  - **3-4**: *Warning* (Further investigation needed)
  - **5-6**: *Warning* (Investigation & changes required soon)
  - **7**: *Critical* (Immediate intervention required)
- **100% Deterministic** (no ML in safety evaluation).

### 2. `shift_monitor.py`
- Tracks continuous ergonomic risk across time.
- **Sustained Risk Invariant**: Only triggers an alert when elevated risk (`warning` or `critical`) persists for **≥120 continuous seconds**.
- Transient spikes (e.g., reaching for a dropped tool for 5 seconds) are **rejected**.
- Graceful initialization without assuming a starting baseline.

### 3. `productivity_tracker.py`
- Detects repetitive task cycles (e.g. hand-molding reach/withdraw motion) using **velocity zero-crossing** on joint angle time series.
- Direction reversals mark cycle boundaries (2 reversals = 1 full cycle).
- Sub-sample zero-crossing time interpolation for zero jitter.
- Rejects noise cycles faster than minimum plausible duration.
- Reports completed cycles, rolling rate (`cycles/hour`), average cycle duration, and cycle duration **standard deviation** (consistency / fatigue indicator).

### 4. `multi_worker_monitor.py`
- Orchestrates independent `ShiftMonitor` and `ProductivityTracker` instances per worker ID.
- Aggregates real-time floor metrics: active alert workers, critical/warning counts, floor safety index, and cycle productivity.

### 5. `supervisor_agent.py`
- Autonomous Gemini-powered supervisory agent with **strictly 4 tools and no others**:
  1. `log_incident`
  2. `notify_supervisor`
  3. `escalate_critical` (MANDATORY on critical risk)
  4. `generate_shift_report`
- **Hard Safety Guarantee**: Cannot directly stop machinery or discipline workers; informs and escalates to human managers only.
- Maintains a tamper-evident, timestamped `action_log` audit trail.

### 6. `skeleton_visualizer.py`
- MediaPipe / COCO standard topology overlay using OpenCV.
- Bone & joint color dynamically encodes risk: **Teal** (Safe), **Amber** (Warning), **Red** (Critical).
- **Anti-Overlap Collision Avoidance**: Uses `cv2.getTextSize` to measure rendered bounding boxes and staggers overlapping labels vertically and horizontally when workers stand adjacent in frame.

---

## 🚀 Google Cloud Deployment

### 1. Direct Cloud Run Deployment
```bash
gcloud run deploy worker-safety \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars GEMINI_API_KEY="your-gemini-key"
```

### 2. Vertex AI Custom Container Serving
Vertex AI automatically injects `AIP_HEALTH_ROUTE` (`/health`), `AIP_PREDICT_ROUTE` (`/predict`), and `AIP_HTTP_PORT` (`8080`).

```bash
# 1. Build and push image to Artifact Registry
gcloud builds submit --tag us-central1-docker.pkg.dev/YOUR_PROJECT/models/worker-safety:v1

# 2. Upload Model to Vertex AI
gcloud ai models upload \
  --region=us-central1 \
  --display-name=worker-safety-rula \
  --container-image-uri=us-central1-docker.pkg.dev/YOUR_PROJECT/models/worker-safety:v1 \
  --container-health-route=/health \
  --container-predict-route=/predict \
  --container-ports=8080

# 3. Deploy to Vertex AI Endpoint
gcloud ai endpoints create --region=us-central1 --display-name=worker-safety-endpoint
gcloud ai endpoints deploy-model ENDPOINT_ID \
  --region=us-central1 \
  --model=MODEL_ID \
  --display-name=worker-safety-deployment \
  --machine-type=n1-standard-2
```

---

## 🧪 Vertex AI REST Prediction Format

### Request (`POST /predict`):
```json
{
  "instances": [
    {
      "worker_id": "WRK-001",
      "shoulder_flexion": 110.0,
      "elbow_flexion": 130.0,
      "wrist_flexion": 25.0,
      "neck_flexion": 30.0,
      "trunk_flexion": 65.0,
      "shoulder_raised": true,
      "arm_abducted": true,
      "trunk_twisted": true
    }
  ]
}
```

### Response:
```json
{
  "predictions": [
    {
      "worker_id": "WRK-001",
      "final_score": 7,
      "action_level": 4,
      "action_description": "Immediate investigation and ergonomic changes required to prevent musculoskeletal injury.",
      "risk_level": "critical",
      "components": {
        "upper_arm": 6,
        "lower_arm": 2,
        "wrist": 3,
        "score_c": 7,
        "neck": 4,
        "trunk": 5,
        "legs": 1,
        "score_d": 7
      }
    }
  ]
}
```

---

## 🔬 Test Suite Execution

Run all verification tests with synthetic datasets:
```bash
python3 -m worker_safety.test_suite
```
