# DevOps Incident Response Environment

An **OpenEnv-compatible reinforcement learning environment** that simulates real-world DevOps failures. An AI agent must diagnose and resolve infrastructure incidents across three difficulty levels.

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
