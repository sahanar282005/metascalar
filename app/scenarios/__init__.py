from app.scenarios.api_crash import ApiCrashScenario
from app.scenarios.db_overload import DbOverloadScenario
from app.scenarios.failed_deployment import FailedDeploymentScenario
from app.scenarios.base import BaseScenario

SCENARIO_REGISTRY = {
    "api_crash": ApiCrashScenario,
    "db_overload": DbOverloadScenario,
    "failed_deployment": FailedDeploymentScenario,
}

__all__ = [
    "SCENARIO_REGISTRY",
    "BaseScenario",
    "ApiCrashScenario",
    "DbOverloadScenario",
    "FailedDeploymentScenario",
]
