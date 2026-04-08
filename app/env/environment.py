"""
DevOps Incident Response Environment — OpenEnv Core Engine
Implements: reset(), step(action), state()
"""
from typing import Optional, Tuple, Dict, Any
from app.scenarios import SCENARIO_REGISTRY, BaseScenario
from app.models.observation import Observation
from app.models.action import Action
from app.models.reward import Reward
import logging

logger = logging.getLogger("devops_env")


class DevOpsEnvironment:
    """
    OpenEnv-compatible environment for DevOps incident response.

    Scenarios:
        - api_crash       (easy)
        - db_overload     (medium)
        - failed_deployment (hard)
    """

    VERSION = "1.0.0"

    def __init__(self, scenario_id: str = "api_crash", seed: int = 42):
        if scenario_id not in SCENARIO_REGISTRY:
            raise ValueError(
                f"Unknown scenario '{scenario_id}'. "
                f"Available: {sorted(SCENARIO_REGISTRY.keys())}"
            )
        self._scenario_id = scenario_id
        self._seed = seed
        self._scenario: Optional[BaseScenario] = None
        self._episode_reward: float = 0.0
        self._episode_steps: int = 0
        self._initialized = False

    # ── OpenEnv Interface ────────────────────────────────────────────────

    def reset(self) -> Observation:
        """Reset environment to initial state and return first observation."""
        ScenarioClass = SCENARIO_REGISTRY[self._scenario_id]
        self._scenario = ScenarioClass(seed=self._seed)
        obs = self._scenario.reset()
        self._episode_reward = 0.0
        self._episode_steps = 0
        self._initialized = True
        logger.info(
            "ENV_RESET | scenario=%s | seed=%d | max_steps=%d",
            self._scenario_id, self._seed, self._scenario.max_steps,
        )
        return obs

    def step(self, action: Action) -> Tuple[Observation, Reward]:
        """
        Apply action to environment.
        Returns (observation, reward).
        Raises RuntimeError if reset() has not been called.
        """
        self._assert_initialized()
        obs, reward = self._scenario.step(action)
        self._episode_reward += reward.total
        self._episode_steps += 1
        logger.info(
            "ENV_STEP | step=%d | action=%s | reward=%.3f | total=%.3f | done=%s | success=%s",
            self._episode_steps,
            action.command,
            reward.total,
            self._episode_reward,
            reward.episode_complete,
            reward.success,
        )
        return obs, reward

    def state(self) -> Dict[str, Any]:
        """
        Return full environment state snapshot (for debugging / serialization).
        """
        self._assert_initialized()
        obs = self._scenario.get_observation()
        return {
            "version": self.VERSION,
            "scenario_id": self._scenario_id,
            "seed": self._seed,
            "episode_steps": self._episode_steps,
            "episode_reward": round(self._episode_reward, 4),
            "is_done": self._scenario.is_done,
            "observation": obs.dict(),
        }

    # ── Helpers ──────────────────────────────────────────────────────────

    def _assert_initialized(self):
        if not self._initialized or self._scenario is None:
            raise RuntimeError(
                "Environment not initialized. Call reset() before step() or state()."
            )

    @property
    def scenario_id(self) -> str:
        return self._scenario_id

    @property
    def available_scenarios(self):
        return sorted(SCENARIO_REGISTRY.keys())

    @property
    def is_done(self) -> bool:
        if self._scenario is None:
            return False
        return self._scenario.is_done
