from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRASHED = "crashed"
    OVERLOADED = "overloaded"
    DEPLOYING = "deploying"
    FAILED = "failed"
    UNKNOWN = "unknown"


class SystemMetrics(BaseModel):
    cpu_usage: float = Field(..., ge=0.0, le=100.0, description="CPU usage percentage")
    memory_usage: float = Field(..., ge=0.0, le=100.0, description="Memory usage percentage")
    request_rate: float = Field(..., ge=0.0, description="Requests per second")
    error_rate: float = Field(..., ge=0.0, le=100.0, description="Error rate percentage")
    response_time_ms: float = Field(..., ge=0.0, description="Average response time in ms")
    active_connections: int = Field(..., ge=0, description="Active DB/service connections")
    db_query_time_ms: float = Field(..., ge=0.0, description="Average DB query time in ms")
    deployment_version: str = Field(..., description="Current deployed version")
    replicas_running: int = Field(..., ge=0, description="Running service replicas")
    replicas_desired: int = Field(..., ge=0, description="Desired service replicas")


class Observation(BaseModel):
    scenario_id: str = Field(..., description="Active scenario identifier")
    step: int = Field(..., ge=0, description="Current step in episode")
    max_steps: int = Field(..., ge=1, description="Maximum allowed steps")
    services: Dict[str, ServiceStatus] = Field(..., description="Status of each service")
    metrics: SystemMetrics = Field(..., description="Current system metrics")
    logs: List[str] = Field(..., description="Recent system log entries")
    incident_resolved: bool = Field(False, description="Whether the incident is resolved")
    incident_description: str = Field(..., description="Human-readable incident description")
    available_actions: List[str] = Field(..., description="Actions available in this state")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extra scenario metadata")

    class Config:
        use_enum_values = True
