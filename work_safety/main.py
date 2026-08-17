"""
main.py
FastAPI application for the worker_safety ergonomic and productivity system.
Provides standard Google Cloud Vertex AI custom prediction container endpoints:
  - AIP_HEALTH_ROUTE (default: /health or /healthz)
  - AIP_PREDICT_ROUTE (default: /predict or /v1/models/worker_safety:predict)
Accepts {"instances": [...]} and returns {"predictions": [...]}.
Also provides multi-worker shift monitoring, cycle tracking, and supervisor agent endpoints.
Deployable directly to Google Cloud Run and Vertex AI Model Serving.
"""

import os
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from worker_safety.rula_assessment import RULAAssessment, RULAResult, RiskLevel
from worker_safety.shift_monitor import ShiftMonitor, WorkerRiskAlert, ShiftSummary
from worker_safety.productivity_tracker import ProductivityTracker, CycleMetrics
from worker_safety.multi_worker_monitor import MultiWorkerMonitor, FloorSummary, WorkerStatus
from worker_safety.supervisor_agent import SupervisorAgent, AgentDecision
from worker_safety.skeleton_visualizer import SkeletonVisualizer, Joint2D, WorkerSkeletonVisual

# Environment configuration for Vertex AI
AIP_HEALTH_ROUTE = os.environ.get("AIP_HEALTH_ROUTE", "/health")
AIP_PREDICT_ROUTE = os.environ.get("AIP_PREDICT_ROUTE", "/predict")
AIP_HTTP_PORT = int(os.environ.get("AIP_HTTP_PORT", os.environ.get("PORT", "8080")))

app = FastAPI(
    title="worker_safety - Vertex AI & Cloud Run Ergonomic Assessment Service",
    description="Factory floor stereo-vision ergonomic risk (RULA) and productivity monitoring API.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global multi-worker floor monitor state
global_monitor = MultiWorkerMonitor(sustained_alert_threshold_seconds=120.0)
global_agent = SupervisorAgent()
global_visualizer = SkeletonVisualizer()


# ==========================================
# VERTEX AI REQUEST / RESPONSE MODELS
# ==========================================

class RULAInstance(BaseModel):
    worker_id: Optional[str] = "WRK-001"
    timestamp: Optional[float] = None
    shoulder_flexion: float = Field(default=10.0, description="Shoulder flexion angle in degrees")
    elbow_flexion: float = Field(default=90.0, description="Elbow flexion angle in degrees")
    wrist_flexion: float = Field(default=0.0, description="Wrist flexion angle in degrees")
    neck_flexion: float = Field(default=5.0, description="Neck flexion angle in degrees")
    trunk_flexion: float = Field(default=0.0, description="Trunk flexion angle in degrees")
    shoulder_raised: bool = False
    arm_abducted: bool = False
    arm_supported: bool = False
    arm_across_midline: bool = False
    wrist_deviation: bool = False
    wrist_twist_end: bool = False
    neck_twisted: bool = False
    neck_side_bend: bool = False
    trunk_twisted: bool = False
    trunk_side_bend: bool = False
    legs_balanced: bool = True
    muscle_use: int = 0
    force_load: int = 0


class VertexPredictRequest(BaseModel):
    instances: List[RULAInstance]
    parameters: Optional[Dict[str, Any]] = None


class VertexPredictResponse(BaseModel):
    predictions: List[Dict[str, Any]]


# ==========================================
# VERTEX AI HEALTH & PREDICTION ROUTES
# ==========================================

@app.get("/health")
@app.get("/healthz")
async def health_check():
    """Health check endpoint for Google Cloud Run and Vertex AI."""
    return {
        "status": "healthy",
        "service": "worker_safety",
        "version": "1.0.0",
        "active_workers": len(global_monitor.latest_worker_statuses),
    }


# If custom AIP_HEALTH_ROUTE is set to something other than /health, register it dynamically
if AIP_HEALTH_ROUTE not in ("/health", "/healthz"):
    @app.get(AIP_HEALTH_ROUTE)
    async def custom_health_check():
        return {"status": "healthy", "service": "worker_safety"}


@app.post("/predict", response_model=VertexPredictResponse)
@app.post("/v1/models/worker_safety:predict", response_model=VertexPredictResponse)
async def predict_rula(request: VertexPredictRequest):
    """
    Standard Vertex AI prediction endpoint.
    Accepts list of joint angle instances, outputs list of deterministic RULA risk assessments.
    """
    predictions = []
    for inst in request.instances:
        result = RULAAssessment.evaluate(
            shoulder_flexion=inst.shoulder_flexion,
            elbow_flexion=inst.elbow_flexion,
            wrist_flexion=inst.wrist_flexion,
            neck_flexion=inst.neck_flexion,
            trunk_flexion=inst.trunk_flexion,
            shoulder_raised=inst.shoulder_raised,
            arm_abducted=inst.arm_abducted,
            arm_supported=inst.arm_supported,
            arm_across_midline=inst.arm_across_midline,
            wrist_deviation=inst.wrist_deviation,
            wrist_twist_end=inst.wrist_twist_end,
            neck_twisted=inst.neck_twisted,
            neck_side_bend=inst.neck_side_bend,
            trunk_twisted=inst.trunk_twisted,
            trunk_side_bend=inst.trunk_side_bend,
            legs_balanced=inst.legs_balanced,
            muscle_use=inst.muscle_use,
            force_load=inst.force_load,
        )
        pred_dict = result.to_dict()
        pred_dict["worker_id"] = inst.worker_id
        predictions.append(pred_dict)

    return VertexPredictResponse(predictions=predictions)


if AIP_PREDICT_ROUTE not in ("/predict", "/v1/models/worker_safety:predict"):
    @app.post(AIP_PREDICT_ROUTE, response_model=VertexPredictResponse)
    async def custom_predict_rula(request: VertexPredictRequest):
        return await predict_rula(request)


# ==========================================
# MULTI-WORKER SHIFT & AGENT API ENDPOINTS
# ==========================================

class WorkerUpdateRequest(BaseModel):
    timestamp: float
    worker_id: str
    joint_angles: Dict[str, float]
    modifiers: Optional[Dict[str, bool]] = None


@app.post("/api/worker/update")
async def update_worker_stream(payload: WorkerUpdateRequest):
    """Feed real-time stereo tracking frame for a worker."""
    rula_res, alert, status_obj = global_monitor.update_worker(
        timestamp=payload.timestamp,
        worker_id=payload.worker_id,
        joint_angles=payload.joint_angles,
        modifiers=payload.modifiers,
    )
    return {
        "status": "success",
        "worker_id": payload.worker_id,
        "rula": rula_res.to_dict(),
        "new_alert": alert.to_dict() if alert else None,
        "worker_status": status_obj.to_dict(),
    }


@app.get("/api/floor/summary")
async def get_floor_summary():
    """Retrieve full aggregate factory floor ergonomic & productivity status."""
    summary = global_monitor.get_floor_summary()
    return summary.to_dict()


@app.post("/api/agent/review")
async def trigger_agent_review():
    """Trigger the Gemini supervisor agent to review floor summary and execute actions."""
    summary = global_monitor.get_floor_summary()
    decision = global_agent.review_floor_summary(summary.to_dict())
    return {
        "decision": decision.to_dict(),
        "action_log_total": len(global_agent.action_log),
        "recent_actions": [a.to_dict() for a in global_agent.action_log[-10:]],
    }


@app.get("/api/agent/audit-log")
async def get_agent_audit_log():
    """Retrieve complete tamper-evident audit action_log."""
    return {
        "total_records": len(global_agent.action_log),
        "records": [a.to_dict() for a in global_agent.action_log],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=AIP_HTTP_PORT)
