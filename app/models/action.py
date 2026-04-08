from pydantic import BaseModel, Field, validator
from enum import Enum
from typing import Optional


class ActionType(str, Enum):
    RESTART_SERVICE = "restart_service"
    SCALE_SERVICE = "scale_service"
    ROLLBACK_DEPLOYMENT = "rollback_deployment"
    CHECK_LOGS = "check_logs"
    DO_NOTHING = "do_nothing"


# Full set of valid action command strings
VALID_ACTIONS = {
    "restart_service:api",
    "restart_service:db",
    "restart_service:worker",
    "scale_service:db",
    "scale_service:api",
    "rollback_deployment",
    "check_logs",
    "do_nothing",
}


class Action(BaseModel):
    command: str = Field(
        ...,
        description="Action command string. Format: '<action_type>:<target>' or '<action_type>'.",
        example="restart_service:api",
    )

    @validator("command")
    def command_must_be_valid(cls, v):
        if v not in VALID_ACTIONS:
            raise ValueError(
                f"Invalid action '{v}'. Must be one of: {sorted(VALID_ACTIONS)}"
            )
        return v

    @property
    def action_type(self) -> ActionType:
        parts = self.command.split(":")
        return ActionType(parts[0])

    @property
    def target(self) -> Optional[str]:
        parts = self.command.split(":")
        return parts[1] if len(parts) > 1 else None

    class Config:
        use_enum_values = True
