# DevOps Incident Response Environment

An **OpenEnv-compatible reinforcement learning environment** that simulates real-world DevOps failures. An AI agent must diagnose and resolve infrastructure incidents across three difficulty levels.

## About This Project

This project provides a comprehensive simulation environment for training and evaluating autonomous DevOps agents. It models realistic infrastructure scenarios where agents must perform diagnostic and remedial actions to resolve system incidents. The environment is fully HTTP-accessible via FastAPI and follows the OpenEnv specification for RL environment standardization.

### Key Features
- **Three Difficulty Levels**: Progressive complexity from simple API crashes to cascading deployment failures
- **OpenEnv Compliant**: Standard RL environment interface compatible with multiple agent frameworks
- **LLM Integration**: Built-in support for AI-powered agents via Hugging Face/OpenAI-compatible APIs
- **Docker Ready**: Production-ready containerization for easy deployment
- **Detailed Observation Space**: Services, metrics, logs, and incident descriptions for informed decision-making

## Technology Stack

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) 0.111+ - Modern async Python web framework
- **Data Validation**: [Pydantic](https://docs.pydantic.dev/) 2.7+ - Type-safe data models
- **API Server**: [Uvicorn](https://www.uvicorn.org/) 0.29+ - ASGI application server
- **LLM Integration**: [OpenAI Python Client](https://github.com/openai/openai-python) - Compatible with Hugging Face APIs
- **Environment Spec**: [OpenEnv Core](https://github.com/openenv-foundation/core) - Standardized RL environment interface
- **Runtime**: Python 3.11+
- **Containerization**: Docker multi-stage builds

---

## Quick Start

### Local (Python)
```bash
pip install -r requirements.txt

# Start the API server
uvicorn app.main:app --reload --port 8000

# Open docs
open http://localhost:8000/docs
```

### Docker
```bash
docker build -t devops-incident-env:1.0.0 .
docker run -p 8000:8000 devops-incident-env:1.0.0
```

### Run inference script
```bash
# Optimal agent on all scenarios
python inference.py --all-scenarios --policy optimal

# Random agent on the hard scenario
python inference.py --scenario failed_deployment --policy random --seed 99
```

---

## Environment Variables

The project supports the following environment variables, particularly for LLM-based agent integration:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_BASE_URL` | No | `https://api-inference.huggingface.co/v1` | Base URL for Hugging Face or OpenAI-compatible API |
| `HF_TOKEN` | No | `` | Hugging Face API authentication token |
| `MODEL_NAME` | No | `` | LLM model identifier (e.g., `meta-llama/Llama-2-7b-hf`) |
| `PYTHONPATH` | No | `/app` | Python module search path (Docker: pre-configured) |
| `PYTHONUNBUFFERED` | No | `1` | Ensures unbuffered logging output |

### Example Configuration

For local development with Hugging Face models:
```bash
export API_BASE_URL="https://api-inference.huggingface.co/v1"
export HF_TOKEN="hf_your_token_here"
export MODEL_NAME="meta-llama/Llama-2-7b-hf"
```

For Docker deployment, pass environment variables via `docker run -e`:
```bash
docker run -p 8000:8000 \
  -e API_BASE_URL="https://api-inference.huggingface.co/v1" \
  -e HF_TOKEN="hf_your_token_here" \
  -e MODEL_NAME="meta-llama/Llama-2-7b-hf" \
  devops-incident-env:1.0.0
```

---

## Scenarios

| Scenario ID         | Difficulty | Max Steps | Incident                                     |
|---------------------|------------|-----------|----------------------------------------------|
| `api_crash`         | Easy       | 8         | API service crashed (OOM kill, all replicas down) |
| `db_overload`       | Medium     | 10        | Database overloaded (500/500 connections)    |
| `failed_deployment` | Hard       | 12        | Bad deployment causing cascading failures    |

### Optimal Solutions

**`api_crash` (Easy)**
```
check_logs            → +0.25 (step 1)
restart_service:api   → +1.95 (step 2, +1.0 action + 1.0 success − 0.05 penalty)
```

**`db_overload` (Medium)**
```
check_logs        → +0.25 (diagnose connection storm)
scale_service:db  → +1.95 (scale + success bonus)
```

**`failed_deployment` (Hard)**
```
check_logs            → +0.25 (identify bad version)
rollback_deployment   → +0.95 (revert to stable)
restart_service:api   → +1.95 (bring API back online)
```

---

## Project Structure

```
devops-incident-env/
├── app/
│   ├── main.py                    # FastAPI server (OpenEnv HTTP interface)
│   ├── env/
│   │   └── environment.py         # DevOpsEnvironment: reset(), step(), state()
│   ├── models/
│   │   ├── observation.py         # Pydantic: Observation, ServiceStatus, SystemMetrics
│   │   ├── action.py              # Pydantic: Action (with validation)
│   │   └── reward.py              # Pydantic: Reward, RewardComponent, constants
│   └── scenarios/
│       ├── base.py                # BaseScenario abstract class
│       ├── api_crash.py           # Scenario 1: API crash (easy)
│       ├── db_overload.py         # Scenario 2: DB overload (medium)
│       └── failed_deployment.py   # Scenario 3: Failed deployment (hard)
├── inference.py                   # Agent runner with strict JSON log output
├── openenv.yaml                   # OpenEnv specification
├── Dockerfile                     # Multi-stage Docker build
├── requirements.txt
└── README.md
```

---

## API Reference

### `POST /reset`
Initialize a new episode.

```json
{
  "scenario_id": "api_crash",
  "seed": 42
}
```

Returns: `{ "observation": { ... } }`

---

### `POST /step`
Apply an action.

```json
{ "action": "restart_service:api" }
```

Returns:
```json
{
  "observation": { "scenario_id": "api_crash", "step": 1, ... },
  "reward": { "total": 1.95, "components": [...], "success": true }
}
```

---

### `GET /state`
Full environment state snapshot (for debugging).

---

### Valid Actions

| Command                | Description                              |
|------------------------|------------------------------------------|
| `restart_service:api`  | Restart the API service                  |
| `restart_service:db`   | Restart the database service             |
| `restart_service:worker` | Restart the worker service             |
| `scale_service:db`     | Horizontally scale the database          |
| `scale_service:api`    | Horizontally scale the API service       |
| `rollback_deployment`  | Roll back to last stable deployment      |
| `check_logs`           | Examine system logs for root cause       |
| `do_nothing`           | Take no action this step                 |

---

## Reward Shaping

| Event             | Reward  |
|-------------------|---------|
| Correct action    | `+1.0`  |
| Partial progress  | `+0.3`  |
| Wrong action      | `-0.2`  |
| Step penalty      | `-0.05` |
| Success bonus     | `+1.0`  |

---

## Observation Schema

```python
class Observation(BaseModel):
    scenario_id: str
    step: int
    max_steps: int
    services: Dict[str, ServiceStatus]   # healthy/degraded/crashed/overloaded/failed
    metrics: SystemMetrics               # CPU, memory, error rate, response time, etc.
    logs: List[str]                      # Recent system log entries
    incident_resolved: bool
    incident_description: str
    available_actions: List[str]
```

---

## Inference Output Format

The `inference.py` script emits **JSON Lines** to `stdout` and human-readable logs to `stderr`.

```jsonl
{"timestamp": "2024-01-01T12:00:00+00:00", "event": "episode_start", "scenario_id": "api_crash", ...}
{"timestamp": "2024-01-01T12:00:00+00:00", "event": "step", "step": 1, "action": "check_logs", "reward_total": 0.25, ...}
{"timestamp": "2024-01-01T12:00:00+00:00", "event": "step", "step": 2, "action": "restart_service:api", "reward_total": 1.95, ...}
{"timestamp": "2024-01-01T12:00:00+00:00", "event": "episode_end", "success": true, "steps_taken": 2, "total_reward": 2.2, ...}
```

Capture structured output:
```bash
python inference.py --scenario api_crash 2>/dev/null | jq .
```

---

## Determinism

All scenarios are fully deterministic given the same `seed`. State transitions are driven purely by action inputs — no hidden randomness.

```bash
# These two runs produce identical output
python inference.py --scenario failed_deployment --seed 42
python inference.py --scenario failed_deployment --seed 42
```

---

## Environment Design

The environment implements a **phase-based state machine** for each scenario:

```
api_crash:
  initial → [restart_service:api] → resolved
  initial → [check_logs] → initial (with richer logs) → [restart_service:api] → resolved

db_overload:
  initial → [check_logs] → initial_diagnosed → [scale_service:db] → resolved
  initial → [scale_service:db] → partial_scaled (no full resolution)

failed_deployment:
  initial → [check_logs] → logs_checked → [rollback_deployment] → rolled_back → [restart_service:api] → resolved
```

This design rewards understanding the system before acting, while still allowing shortcuts that yield partial rewards.
