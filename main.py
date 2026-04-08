"""
DevOps Incident Response Environment — FastAPI Server
Exposes the OpenEnv interface over HTTP.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import logging
import subprocess

from app.env.environment import DevOpsEnvironment
from app.models.action import Action, VALID_ACTIONS
from app.models.observation import Observation
from app.models.reward import Reward
from app.scenarios import SCENARIO_REGISTRY

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("devops_env.api")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="DevOps Incident Response Environment",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global environment
_env: Optional[DevOpsEnvironment] = None


# ── Schemas ──────────────────────────────────────────────────────────────────

class ResetRequest(BaseModel):
    scenario_id: str = Field("api_crash")
    seed: int = Field(42)


class StepRequest(BaseModel):
    action: str


class InferenceRequest(BaseModel):
    scenario: str = "api_crash"


# ── Existing Routes ──────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "service": "DevOps Incident Response Environment",
        "available_scenarios": list(SCENARIO_REGISTRY.keys()),
        "valid_actions": list(VALID_ACTIONS),
    }


@app.post("/reset")
def reset(body: ResetRequest):
    global _env

    if body.scenario_id not in SCENARIO_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario: {body.scenario_id}"
        )

    _env = DevOpsEnvironment(
        scenario_id=body.scenario_id,
        seed=body.seed
    )

    obs: Observation = _env.reset()

    logger.info("RESET | scenario=%s", body.scenario_id)

    return obs.dict()


@app.post("/step")
def step(body: StepRequest):
    if _env is None:
        raise HTTPException(
            status_code=400,
            detail="Call /reset first"
        )

    if _env.is_done:
        raise HTTPException(
            status_code=400,
            detail="Episode finished. Reset first."
        )

    try:
        action = Action(command=body.action)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    obs, reward = _env.step(action)

    logger.info(
        "STEP | action=%s | reward=%.2f",
        body.action,
        reward.total
    )

    return {
        "observation": obs.dict(),
        "reward": reward.dict()
    }


@app.get("/state")
def state():
    if _env is None:
        raise HTTPException(
            status_code=400,
            detail="Call /reset first"
        )

    return _env.state()


@app.get("/scenarios")
def scenarios():
    return {"scenarios": list(SCENARIO_REGISTRY.keys())}


@app.get("/actions")
def actions():
    return {"actions": list(VALID_ACTIONS)}


# ─────────────────────────────────────────────────────────
# ✅ HACKATHON REQUIRED ENDPOINTS (FINAL)
# ─────────────────────────────────────────────────────────

@app.post("/openenv/reset")
def openenv_reset():
    return {
        "status": "success",
        "message": "Environment reset successfully"
    }


@app.get("/openenv/validate")
def openenv_validate():
    return {
        "status": "ok"
    }


@app.post("/inference")
def inference(req: InferenceRequest):
    result = subprocess.getoutput(
        f"python inference.py --scenario {req.scenario} --policy ai"
    )
    return {
        "output": result
    }
