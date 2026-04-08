"""
Scenario: Database Overload (Medium)
The DB is overwhelmed with connections. Agent must scale the DB, but only
after checking logs first (otherwise wrong order → partial reward only).
Optimal solution: check_logs → scale_service:db
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


class DbOverloadScenario(BaseScenario):
    scenario_id = "db_overload"
    difficulty = "medium"
    max_steps = 10

    _logs_checked: bool = False
    _db_scaled: bool = False

    def reset(self) -> Observation:
        self._step = 0
        self._resolved = False
        self._logs_checked = False
        self._db_scaled = False
        return self.get_observation()

    def get_observation(self) -> Observation:
        if self._resolved:
            services = {
                "api": ServiceStatus.HEALTHY,
                "db": ServiceStatus.HEALTHY,
                "worker": ServiceStatus.HEALTHY,
            }
            metrics = SystemMetrics(
                cpu_usage=35.0,
                memory_usage=55.0,
                request_rate=300.0,
                error_rate=0.1,
                response_time_ms=42.0,
                active_connections=120,
                db_query_time_ms=8.0,
                deployment_version="v1.9.4",
                replicas_running=3,
                replicas_desired=3,
            )
            logs = [
                "[INFO] DB replica count scaled to 3",
                "[INFO] Connection pool pressure relieved",
                "[INFO] Query latency returned to normal (<10ms)",
                "[INFO] All API health checks passing",
            ]
            description = "Incident resolved. Database scaled and healthy."
        elif self._db_scaled and not self._resolved:
            # Scaling without checking logs → partial state
            services = {
                "api": ServiceStatus.DEGRADED,
                "db": ServiceStatus.DEGRADED,
                "worker": ServiceStatus.HEALTHY,
            }
            metrics = self._degraded_metrics()
            logs = self._build_logs()
            description = (
                "DB scaling initiated without diagnosing root cause. "
                "Partial improvement observed but issue persists."
            )
        else:
            services = {
                "api": ServiceStatus.DEGRADED,
                "db": ServiceStatus.OVERLOADED,
                "worker": ServiceStatus.DEGRADED,
            }
            metrics = self._overloaded_metrics()
            logs = self._build_logs()
            description = (
                "INCIDENT: Database is overloaded. Max connections reached (500/500). "
                "API response times degraded to 4000ms. Queries timing out."
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
                "scale_service:db",
                "scale_service:api",
                "rollback_deployment",
                "check_logs",
                "do_nothing",
            ],
            metadata={"difficulty": self.difficulty, "logs_checked": self._logs_checked},
        )

    def _overloaded_metrics(self) -> SystemMetrics:
        return SystemMetrics(
            cpu_usage=98.0,
            memory_usage=94.0,
            request_rate=450.0,
            error_rate=62.0,
            response_time_ms=4200.0,
            active_connections=500,
            db_query_time_ms=8500.0,
            deployment_version="v1.9.4",
            replicas_running=1,
            replicas_desired=3,
        )

    def _degraded_metrics(self) -> SystemMetrics:
        return SystemMetrics(
            cpu_usage=71.0,
            memory_usage=78.0,
            request_rate=300.0,
            error_rate=18.0,
            response_time_ms=900.0,
            active_connections=300,
            db_query_time_ms=350.0,
            deployment_version="v1.9.4",
            replicas_running=2,
            replicas_desired=3,
        )

    def _build_logs(self) -> List[str]:
        base = [
            "[CRITICAL] DB connections maxed: 500/500 active connections",
            "[ERROR] Connection pool exhausted for api-service",
            "[ERROR] Query timeout after 8500ms: SELECT * FROM events WHERE ...",
            "[ERROR] Query timeout after 8200ms: INSERT INTO audit_log ...",
            "[WARN]  Worker service falling back to in-memory queue",
            "[WARN]  API endpoint /v1/data returning 502 for 62% of requests",
        ]
        if self._logs_checked:
            base.append(
                "[INFO] Log analysis: Connection storm detected. "
                "Root cause: single DB replica overwhelmed. Scale horizontally."
            )
        return base

    def step(self, action: Action) -> Tuple[Observation, Reward]:
        self._step += 1
        components: list[RewardComponent] = [self._step_penalty()]
        cmd = action.command

        if cmd == "check_logs":
            self._logs_checked = True
            components.append(RewardComponent(
                name="partial_progress",
                value=REWARD_PARTIAL_PROGRESS,
                reason="Checking logs is essential to diagnose DB overload correctly",
            ))
            reward = Reward.build(components)

        elif cmd == "scale_service:db":
            if self._logs_checked:
                # Optimal path: checked logs first
                self._db_scaled = True
                self._resolved = True
                components.append(RewardComponent(
                    name="correct_action",
                    value=REWARD_CORRECT_ACTION,
                    reason="Scaling DB after diagnosis is the correct resolution",
                ))
                components.append(RewardComponent(
                    name="success_bonus",
                    value=REWARD_SUCCESS_BONUS,
                    reason="Incident fully resolved",
                ))
                reward = Reward.build(components, episode_complete=True, success=True)
            else:
                # Scaling without diagnosis: partial only
                self._db_scaled = True
                components.append(RewardComponent(
                    name="partial_progress",
                    value=REWARD_PARTIAL_PROGRESS,
                    reason="Scaling DB helps but diagnosing first yields full resolution",
                ))
                reward = Reward.build(components)

        elif cmd == "do_nothing":
            components.append(RewardComponent(
                name="wrong_action",
                value=REWARD_WRONG_ACTION,
                reason="DB overload worsens without intervention",
            ))
            reward = Reward.build(components)

        elif cmd in ("restart_service:api", "scale_service:api"):
            components.append(RewardComponent(
                name="wrong_action",
                value=REWARD_WRONG_ACTION,
                reason="The bottleneck is the database, not the API service",
            ))
            reward = Reward.build(components)

        else:
            components.append(RewardComponent(
                name="wrong_action",
                value=REWARD_WRONG_ACTION,
                reason=f"Action '{cmd}' does not address DB overload",
            ))
            reward = Reward.build(components)

        if self._step >= self.max_steps and not self._resolved:
            reward.episode_complete = True

        return self.get_observation(), reward
