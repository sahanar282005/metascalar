#!/usr/bin/env python3
import argparse
import time
import os
import random
from typing import List, Optional

from agent import HuggingFaceAgent
from app.env.environment import DevOpsEnvironment
from app.models.action import Action
from app.models.observation import Observation

# ── Policies ─────────────────────────────────────────────────────────────

OPTIMAL_POLICIES = {
    "api_crash": ["check_logs", "restart_service:api"],
    "db_overload": ["check_logs", "scale_service:db"],
    "failed_deployment": ["check_logs", "rollback_deployment", "restart_service:api"],
}


def optimal_policy(scenario_id: str, step: int) -> str:
    steps = OPTIMAL_POLICIES.get(scenario_id, ["do_nothing"])
    if step < len(steps):
        return steps[step]
    return "do_nothing"


def random_policy(obs: Observation) -> str:
    return random.choice(obs.available_actions)


# ── HF Agent Singleton ───────────────────────────────────────────────────

_hf_agent: Optional[HuggingFaceAgent] = None


def get_hf_agent() -> HuggingFaceAgent:
    global _hf_agent
    if _hf_agent is None:
        _hf_agent = HuggingFaceAgent()
    return _hf_agent


# ── RUN EPISODE ──────────────────────────────────────────────────────────

def run_episode(scenario_id: str, seed: int = 42, policy: str = "optimal"):

    env = DevOpsEnvironment(scenario_id=scenario_id, seed=seed)
    obs: Observation = env.reset()

    # ✅ START FORMAT
    print(f"[START] task={scenario_id} env=openenv model={os.getenv('MODEL_NAME')}")

    total_reward = 0.0
    steps_taken = 0

    hf_agent = None
    if policy == "ai":
        try:
            hf_agent = get_hf_agent()
        except Exception:
            policy = "random"

    while not env.is_done:

        # Choose action
        if policy == "optimal":
            cmd = optimal_policy(scenario_id, steps_taken)

        elif policy == "ai" and hf_agent is not None:
            cmd = hf_agent.decide_action(obs.model_dump())

        else:
            cmd = random_policy(obs)

        # Apply action
        try:
            action = Action(command=cmd)
        except Exception:
            action = Action(command="do_nothing")

        obs, reward = env.step(action)

        total_reward += reward.total
        steps_taken += 1

        # ✅ STEP FORMAT
        print(
            f"[STEP] step={steps_taken} action={action.command} "
            f"reward={reward.total:.2f} done={reward.episode_complete} error=null"
        )

        if reward.episode_complete:
            break

    success = obs.incident_resolved

    # ✅ END FORMAT
    print(
        f"[END] success={success} steps={steps_taken} "
        f"score={total_reward:.2f} rewards={total_reward:.2f}"
    )


# ── CLI ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--scenario",
        choices=["api_crash", "db_overload", "failed_deployment"],
        default="api_crash",
    )

    parser.add_argument(
        "--policy",
        choices=["optimal", "random", "ai"],
        default="optimal",
    )

    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()

    run_episode(
        scenario_id=args.scenario,
        seed=args.seed,
        policy=args.policy,
    )


if __name__ == "__main__":
    main()