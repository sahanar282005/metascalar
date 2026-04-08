from pydantic import BaseModel, Field
from typing import List


class RewardComponent(BaseModel):
    name: str = Field(..., description="Name of this reward component")
    value: float = Field(..., description="Reward value of this component")
    reason: str = Field(..., description="Human-readable explanation")


# Reward shaping constants
REWARD_CORRECT_ACTION = 1.0
REWARD_PARTIAL_PROGRESS = 0.3
REWARD_WRONG_ACTION = -0.2
REWARD_STEP_PENALTY = -0.05
REWARD_SUCCESS_BONUS = 1.0
REWARD_DO_NOTHING = -0.1


class Reward(BaseModel):
    total: float = Field(..., description="Total reward for this step")
    components: List[RewardComponent] = Field(
        default_factory=list, description="Breakdown of reward components"
    )
    episode_complete: bool = Field(False, description="Whether the episode has ended")
    success: bool = Field(False, description="Whether the incident was resolved")

    @classmethod
    def build(
        cls,
        components: List[RewardComponent],
        episode_complete: bool = False,
        success: bool = False,
    ) -> "Reward":
        total = sum(c.value for c in components)
        return cls(
            total=total,
            components=components,
            episode_complete=episode_complete,
            success=success,
        )
