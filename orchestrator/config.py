"""Orchestrator Configuration"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum


class ExecutionMode(Enum):
    """Execution modes for orchestrator"""
    SEQUENTIAL = "sequential"  # One agent after another
    PARALLEL = "parallel"      # Multiple agents simultaneously
    HYBRID = "hybrid"          # Mix of sequential and parallel


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator"""
    
    # Execution settings
    mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    max_retries: int = 3
    timeout_seconds: int = 300
    
    # Logging and monitoring
    enable_logging: bool = True
    log_level: str = "INFO"
    enable_metrics: bool = True
    
    # State management
    enable_state_persistence: bool = False
    state_storage_path: Optional[str] = None
    
    # Workflow settings
    allow_agent_feedback: bool = True
    enable_rollback: bool = True
    max_iterations: int = 10
    
    # Custom settings
    extra_config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "mode": self.mode.value,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "enable_logging": self.enable_logging,
            "log_level": self.log_level,
            "enable_metrics": self.enable_metrics,
            "enable_state_persistence": self.enable_state_persistence,
            "state_storage_path": self.state_storage_path,
            "allow_agent_feedback": self.allow_agent_feedback,
            "enable_rollback": self.enable_rollback,
            "max_iterations": self.max_iterations,
            "extra_config": self.extra_config,
        }
