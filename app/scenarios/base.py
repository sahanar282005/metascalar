from abc import ABC, abstractmethod
from typing import Tuple

from app.models.action import Action
from app.models.observation import Observation
from app.models.reward import Reward


class BaseScenario(ABC):
    scenario_id: str
    difficulty: str
    max_steps: int

    def __init__(self, seed: int = 42):
        self.seed = seed

    @abstractmethod
    def reset(self) -> Observation:
        raise NotImplementedError

    @abstractmethod
    def get_observation(self) -> Observation:
        raise NotImplementedError

    @abstractmethod
    def step(self, action: Action) -> Tuple[Observation, Reward]:
        raise NotImplementedError

    def _step_penalty(self):
        from app.models.reward import RewardComponent

        return RewardComponent(
            name="step_penalty",
            value=-0.05,
            reason="Penalty for taking a step",
        )

    def _wrong_action_penalty(self):
        from app.models.reward import RewardComponent

        return RewardComponent(
            name="wrong_action",
            value=-0.20,
            reason="Penalty for incorrect action",
        )

    def _success_reward(self):
        from app.models.reward import RewardComponent

        return RewardComponent(
            name="success",
            value=1.0,
            reason="Successful resolution",
        )

    @property
    def is_done(self) -> bool:
        resolved = getattr(self, "_resolved", False)
        step = getattr(self, "_step", 0)
        return resolved or step >= self.max_steps
