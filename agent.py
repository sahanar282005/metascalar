import logging
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI
from app.models.action import VALID_ACTIONS

logger = logging.getLogger("hf_agent")


class HuggingFaceAgent:
    """AI-based agent using Hugging Face via OpenAI-compatible API."""

    def __init__(self):
        self.client = OpenAI(
            base_url=os.getenv("API_BASE_URL"),
            api_key=os.getenv("HF_TOKEN")
        )

        self.model_name = os.getenv("MODEL_NAME")
        self.valid_actions = sorted(VALID_ACTIONS)

        if not self.model_name:
            raise ValueError("MODEL_NAME environment variable not set")

        logger.info("HuggingFaceAgent initialized with model: %s", self.model_name)

    def _build_prompt(self, observation: Dict[str, Any]) -> str:
        services = observation.get("services", {})
        metrics = observation.get("metrics", {})
        logs: List[str] = observation.get("logs", []) or []

        services_str = ", ".join(f"{k}={v}" for k, v in services.items())
        logs_str = "\n".join(logs[-5:]) if logs else "No logs available"

        prompt = (
            "You are a DevOps AI agent.\n"
            "Choose EXACTLY ONE action from the valid actions.\n\n"
            f"Incident: {observation.get('incident_description')}\n"
            f"Services: {services_str}\n"
            f"Error Rate: {metrics.get('error_rate', 0)}%\n\n"
            f"Logs:\n{logs_str}\n\n"
            f"Valid Actions: {', '.join(self.valid_actions)}\n\n"
            "Respond ONLY with the exact action string."
        )

        return prompt

    def _normalize_action(self, text: str) -> Optional[str]:
        if not text:
            return None

        text = text.strip().lower()

        for action in self.valid_actions:
            if action == text:
                return action

        for action in self.valid_actions:
            if action in text:
                return action

        if "restart" in text and "api" in text:
            return "restart_service:api"
        if "restart" in text and "db" in text:
            return "restart_service:db"
        if "restart" in text and "worker" in text:
            return "restart_service:worker"
        if "scale" in text and "db" in text:
            return "scale_service:db"
        if "rollback" in text:
            return "rollback_deployment"
        if "log" in text:
            return "check_logs"

        return None

    def _call_model(self, prompt: str) -> Optional[str]:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.warning("LLM call failed: %s", e)
            return None

    def decide_action(self, observation: Dict[str, Any]) -> str:
        try:
            prompt = self._build_prompt(observation)
            output = self._call_model(prompt)
            action = self._normalize_action(output or "")

            if action:
                return action

            logger.warning("Invalid model output: %s", output)

        except Exception as e:
            logger.warning("Agent error: %s", e)

        # Fallback (REQUIRED for robustness)
        services = observation.get("services", {})

        if services.get("api") == "crashed":
            return "restart_service:api"

        if services.get("db") == "down":
            return "restart_service:db"

        if services.get("worker") == "stuck":
            return "restart_service:worker"

        return "check_logs"