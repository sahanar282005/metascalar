"""
Scenario: Failed Deployment (Hard)
A bad deployment is causing cascading failures across services.
The agent must: check_logs → rollback_deployment → restart_service:api
Optimal solution requires 3 correct sequential steps.
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

# Resolution phases
PHASE_INITIAL = "initial"
PHASE_LOGS_CHECKED = "logs_checked"
PHASE_ROLLED_BACK = "rolled_back"
PHASE_RESOLVED = "resolved"


class FailedDeploymentScenario(BaseScenario):
    scenario_id = "failed_deployment"
    difficulty = "hard"
    max_steps = 12

    def reset(self) -> Observation:
        self._step = 0
        self._resolved = False
        self._phase = PHASE_INITIAL
        return self.get_observation()

    def get_observation(self) -> Observation:
        phase = self._phase

        if phase == PHASE_RESOLVED:
            services = {
                "api": ServiceStatus.HEALTHY,
                "db": ServiceStatus.HEALTHY,
                "worker": ServiceStatus.HEALTHY,
            }
            metrics = SystemMetrics(
                cpu_usage=28.0,
                memory_usage=48.0,
                request_rate=250.0,
                error_rate=0.0,
                response_time_ms=55.0,
                active_connections=80,
                db_query_time_ms=10.0,
                deployment_version="v3.1.0",
                replicas_running=3,
                replicas_desired=3,
            )
            logs = [
                "[INFO] Rollback to v3.1.0 completed successfully",
                "[INFO] API service restarted on stable version",
                "[INFO] All health checks passing",
                "[INFO] Error rate returned to 0%",
                "[INFO] Deployment incident resolved",
            ]
            description = "Incident resolved. Rolled back to v3.1.0 and restarted API."

        elif phase == PHASE_ROLLED_BACK:
            services = {
                "api": ServiceStatus.CRASHED,
                "db": ServiceStatus.HEALTHY,
                "worker": ServiceStatus.DEGRADED,
            }
            metrics = SystemMetrics(
                cpu_usage=15.0,
                memory_usage=30.0,
                request_rate=0.0,
                error_rate=100.0,
                response_time_ms=0.0,
                active_connections=20,
                db_query_time_ms=12.0,
                deployment_version="v3.1.0",
                replicas_running=0,
                replicas_desired=3,
            )
            logs = [
                "[INFO] Rollback to v3.1.0 initiated",
                "[INFO] Bad deployment v3.2.0-rc1 terminated",
                "[WARN] API service down during rollback — restart required",
                "[INFO] DB schema rollback successful",
            ]
            description = (
                "Rollback complete. Deployment reverted to v3.1.0. "
                "API service needs a restart to come back online."
            )

        elif phase == PHASE_LOGS_CHECKED:
            services = {
                "api": ServiceStatus.FAILED,
                "db": ServiceStatus.DEGRADED,
                "worker": ServiceStatus.FAILED,
            }
            metrics = self._failing_metrics(version="v3.2.0-rc1")
            logs = self._build_logs(analyzed=True)
            description = (
                "Log analysis complete. Bad deployment v3.2.0-rc1 contains a "
                "null-pointer bug in the auth middleware. Rollback to v3.1.0 required."
            )

        else:  # PHASE_INITIAL
            services = {
                "api": ServiceStatus.FAILED,
                "db": ServiceStatus.DEGRADED,
                "worker": ServiceStatus.FAILED,
            }
            metrics = self._failing_metrics(version="v3.2.0-rc1")
            logs = self._build_logs(analyzed=False)
            description = (
                "INCIDENT: Deployment v3.2.0-rc1 has caused cascading failures. "
                "API and worker services failing. DB degraded. Root cause unknown."
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
                "restart_service:worker",
                "scale_service:db",
                "rollback_deployment",
                "check_logs",
                "do_nothing",
            ],
            metadata={
                "difficulty": self.difficulty,
                "phase": phase,
                "bad_version": "v3.2.0-rc1",
                "stable_version": "v3.1.0",
            },
        )

    def _failing_metrics(self, version: str) -> SystemMetrics:
        return SystemMetrics(
            cpu_usage=89.0,
            memory_usage=91.0,
            request_rate=5.0,
            error_rate=97.0,
            response_time_ms=12000.0,
            active_connections=450,
            db_query_time_ms=4500.0,
            deployment_version=version,
            replicas_running=1,
            replicas_desired=3,
        )

    def _build_logs(self, analyzed: bool) -> List[str]:
        base = [
            "[CRITICAL] Deployment v3.2.0-rc1 failed post-deploy health check",
            "[ERROR] NullPointerException in AuthMiddleware.validateToken() line 87",
            "[ERROR] API pod crash-looping: 97 restarts in 10 minutes",
            "[ERROR] Worker service unable to reach API: connection refused",
            "[WARN]  DB connections spiking due to failed retry storms",
            "[ERROR] 97% of requests returning HTTP 500 Internal Server Error",
        ]
        if analyzed:
            base.append(
                "[INFO] Root cause identified: v3.2.0-rc1 introduced breaking change "
                "in auth token validation. Stable version: v3.1.0. Action: rollback."
            )
        return base

    def step(self, action: Action) -> Tuple[Observation, Reward]:
        self._step += 1
        components: list[RewardComponent] = [self._step_penalty()]
        cmd = action.command
        phase = self._phase

        # ── Phase-aware action evaluation ──────────────────────────────────

        if phase == PHASE_INITIAL:
            if cmd == "check_logs":
                self._phase = PHASE_LOGS_CHECKED
                components.append(RewardComponent(
                    name="partial_progress",
                    value=REWARD_PARTIAL_PROGRESS,
                    reason="Checking logs reveals the bad deployment as root cause",
                ))
                reward = Reward.build(components)

            elif cmd == "rollback_deployment":
                # Partially useful even without logs
                self._phase = PHASE_ROLLED_BACK
                components.append(RewardComponent(
                    name="partial_progress",
                    value=REWARD_PARTIAL_PROGRESS * 0.5,
                    reason="Rollback without diagnosis works but is riskier",
                ))
                reward = Reward.build(components)

            elif cmd in ("restart_service:api", "restart_service:worker"):
                # Restarting into a bad deployment does nothing
                components.append(RewardComponent(
                    name="wrong_action",
                    value=REWARD_WRONG_ACTION,
                    reason="Restarting services on a bad deployment won't fix the crash loop",
                ))
                reward = Reward.build(components)

            else:
                components.append(RewardComponent(
                    name="wrong_action",
                    value=REWARD_WRONG_ACTION,
                    reason=f"Action '{cmd}' is not appropriate for a failed deployment",
                ))
                reward = Reward.build(components)

        elif phase == PHASE_LOGS_CHECKED:
            if cmd == "rollback_deployment":
                self._phase = PHASE_ROLLED_BACK
                components.append(RewardComponent(
                    name="correct_action",
                    value=REWARD_CORRECT_ACTION,
                    reason="Rollback after log analysis is the correct next step",
                ))
                reward = Reward.build(components)

            elif cmd == "check_logs":
                # Redundant
                components.append(RewardComponent(
                    name="wrong_action",
                    value=REWARD_WRONG_ACTION * 0.5,
                    reason="Logs already checked; this wastes a step",
                ))
                reward = Reward.build(components)

            else:
                components.append(RewardComponent(
                    name="wrong_action",
                    value=REWARD_WRONG_ACTION,
                    reason=f"After diagnosing bad deployment, rollback is required, not '{cmd}'",
                ))
                reward = Reward.build(components)

        elif phase == PHASE_ROLLED_BACK:
            if cmd == "restart_service:api":
                self._phase = PHASE_RESOLVED
                self._resolved = True
                components.append(RewardComponent(
                    name="correct_action",
                    value=REWARD_CORRECT_ACTION,
                    reason="Restarting API after rollback completes the resolution",
                ))
                components.append(RewardComponent(
                    name="success_bonus",
                    value=REWARD_SUCCESS_BONUS,
                    reason="Full incident resolved in optimal sequence",
                ))
                reward = Reward.build(components, episode_complete=True, success=True)

            elif cmd == "check_logs":
                components.append(RewardComponent(
                    name="partial_progress",
                    value=REWARD_PARTIAL_PROGRESS * 0.5,
                    reason="Logs suggest restarting the API service after rollback",
                ))
                reward = Reward.build(components)

            else:
                components.append(RewardComponent(
                    name="wrong_action",
                    value=REWARD_WRONG_ACTION,
                    reason=f"After rollback, API restart is needed, not '{cmd}'",
                ))
                reward = Reward.build(components)

        else:
            # PHASE_RESOLVED — should not reach here
            reward = Reward.build(components, episode_complete=True, success=True)

        if self._step >= self.max_steps and not self._resolved:
            reward.episode_complete = True

        return self.get_observation(), reward
