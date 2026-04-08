"""
Scenario: API Service Crash (Easy)
The API service has crashed with a 503 error. The agent must restart it.
Optimal solution: restart_service:api
"""
from typing import Tuple, List
from app.scenarios.base import BaseScenario
from app.models.observation import Observation, ServiceStatus, SystemMetrics
from app.models.action import Action
from app.models.reward import (
    Reward, RewardComponent,
    REWARD_CORRECT_ACTION, REWARD_PARTIAL_PROGRESS,
    REWARD_WRONG_ACTION, REWARD_STEP_PENALTY, REWARD_SUCCESS_BONUS,
)


class ApiCrashScenario(BaseScenario):
    scenario_id = "api_crash"
    difficulty = "easy"
    max_steps = 8

    # Internal state flags
    _logs_checked: bool = False
    _api_restarted: bool = False

    def reset(self) -> Observation:
        self._step = 0
        self._resolved = False
        self._logs_checked = False
        self._api_restarted = False
        return self.get_observation()

    def get_observation(self) -> Observation:
        if self._resolved:
            services = {
                "api": ServiceStatus.HEALTHY,
                "db": ServiceStatus.HEALTHY,
                "worker": ServiceStatus.HEALTHY,
            }
            metrics = SystemMetrics(
                cpu_usage=22.0,
                memory_usage=45.0,
                request_rate=120.0,
                error_rate=0.0,
                response_time_ms=85.0,
                active_connections=30,
                db_query_time_ms=12.0,
                deployment_version="v2.3.1",
                replicas_running=3,
                replicas_desired=3,
            )
            logs = [
                "[INFO] API service restarted successfully",
                "[INFO] Health checks passing",
                "[INFO] Traffic restored to all replicas",
            ]
            description = "Incident resolved. API service is healthy."
        else:
            services = {
                "api": ServiceStatus.CRASHED,
                "db": ServiceStatus.HEALTHY,
                "worker": ServiceStatus.HEALTHY,
            }
            metrics = SystemMetrics(
                cpu_usage=0.5,
                memory_usage=12.0,
                request_rate=0.0,
                error_rate=100.0,
                response_time_ms=0.0,
                active_connections=0,
                db_query_time_ms=12.0,
                deployment_version="v2.3.1",
                replicas_running=0,
                replicas_desired=3,
            )
            logs = self._build_logs()
            description = (
                "INCIDENT: API service has crashed. All replicas are down. "
                "503 errors returned to clients. Immediate restart required."
            )

        return Observation(
            scenario_id=self.scenario_id,
            step=self._step,
            max_steps=self.max_steps,
            services=services,
            metrics=metrics,
            logs=logs,
            incident_resolved=self._resolved,
            incident_description=description,
            available_actions=[
                "restart_service:api",
                "restart_service:db",
                "rollback_deployment",
                "check_logs",
                "do_nothing",
            ],
            metadata={"difficulty": self.difficulty},
        )

    def _build_logs(self) -> List[str]:
        base = [
            "[CRITICAL] API service process exited with code 137 (OOM Kill)",
            "[ERROR] Readiness probe failed for api-pod-0: connection refused :8080",
            "[ERROR] Readiness probe failed for api-pod-1: connection refused :8080",
            "[ERROR] Readiness probe failed for api-pod-2: connection refused :8080",
            "[WARN]  LoadBalancer health check failed: 0/3 healthy backends",
            "[ERROR] HTTP 503 Service Unavailable returned to all clients",
        ]
        if self._logs_checked:
            base.append("[INFO] Log analysis: OOM kill detected, process restart will recover service")
        return base

    def step(self, action: Action) -> Tuple[Observation, Reward]:
        self._step += 1
        components: list[RewardComponent] = [self._step_penalty()]

        cmd = action.command

        if cmd == "restart_service:api":
            # Correct action — resolves the incident
            self._api_restarted = True
            self._resolved = True
            components.append(RewardComponent(
                name="correct_action",
                value=REWARD_CORRECT_ACTION,
                reason="restart_service:api directly resolves an API crash",
            ))
            components.append(RewardComponent(
                name="success_bonus",
                value=REWARD_SUCCESS_BONUS,
                reason="Incident fully resolved",
            ))
            reward = Reward.build(components, episode_complete=True, success=True)

        elif cmd == "check_logs":
            # Partial credit — helpful diagnostic step
            self._logs_checked = True
            components.append(RewardComponent(
                name="partial_progress",
                value=REWARD_PARTIAL_PROGRESS,
                reason="Checking logs is a valid diagnostic step before acting",
            ))
            reward = Reward.build(components)

        elif cmd == "do_nothing":
            components.append(RewardComponent(
                name="wrong_action",
                value=REWARD_WRONG_ACTION,
                reason="Doing nothing prolongs the outage",
            ))
            reward = Reward.build(components)

        else:
            # Wrong service restart or wrong action
            components.append(RewardComponent(
                name="wrong_action",
                value=REWARD_WRONG_ACTION,
                reason=f"Action '{cmd}' does not address a crashed API service",
            ))
            reward = Reward.build(components)

        if self._step >= self.max_steps and not self._resolved:
            reward.episode_complete = True

        return self.get_observation(), reward
