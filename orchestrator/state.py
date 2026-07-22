"""Shared State Management for Multi-Agent System"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime
import json


class ExecutionStatus(Enum):
    """Execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    CANCELLED = "cancelled"


@dataclass
class ExecutionLog:
    """Log entry for agent execution"""
    agent_name: str
    status: ExecutionStatus
    timestamp: datetime
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log to dictionary"""
        return {
            "agent_name": self.agent_name,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }


@dataclass
class OrchestrationState:
    """Central state management for orchestration"""
    
    # Execution context
    execution_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Shared data between agents
    shared_context: Dict[str, Any] = field(default_factory=dict)
    
    # Agent-specific data
    agent_outputs: Dict[str, Any] = field(default_factory=dict)
    agent_errors: Dict[str, str] = field(default_factory=dict)
    
    # Execution history
    execution_logs: List[ExecutionLog] = field(default_factory=list)
    
    # Workflow tracking
    completed_agents: List[str] = field(default_factory=list)
    pending_agents: List[str] = field(default_factory=list)
    failed_agents: List[str] = field(default_factory=list)
    
    # Rollback support
    checkpoint_history: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_context(self, key: str, value: Any) -> None:
        """Update shared context"""
        self.shared_context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Retrieve value from shared context"""
        return self.shared_context.get(key, default)
    
    def set_agent_output(self, agent_name: str, output: Dict[str, Any]) -> None:
        """Store agent output"""
        self.agent_outputs[agent_name] = output
    
    def get_agent_output(self, agent_name: str, default: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Retrieve agent output"""
        return self.agent_outputs.get(agent_name, default or {})
    
    def set_agent_error(self, agent_name: str, error: str) -> None:
        """Store agent error"""
        self.agent_errors[agent_name] = error
        if agent_name in self.failed_agents:
            return
        self.failed_agents.append(agent_name)
        if agent_name in self.pending_agents:
            self.pending_agents.remove(agent_name)
    
    def add_log(self, log: ExecutionLog) -> None:
        """Add execution log"""
        self.execution_logs.append(log)
    
    def mark_agent_completed(self, agent_name: str) -> None:
        """Mark agent as completed"""
        if agent_name not in self.completed_agents:
            self.completed_agents.append(agent_name)
        if agent_name in self.pending_agents:
            self.pending_agents.remove(agent_name)
        if agent_name in self.failed_agents:
            self.failed_agents.remove(agent_name)
    
    def create_checkpoint(self, checkpoint_id: str) -> None:
        """Create state checkpoint for rollback"""
        self.checkpoint_history[checkpoint_id] = {
            "shared_context": self.shared_context.copy(),
            "agent_outputs": self.agent_outputs.copy(),
            "completed_agents": self.completed_agents.copy(),
            "timestamp": datetime.now().isoformat(),
        }
    
    def rollback_to_checkpoint(self, checkpoint_id: str) -> bool:
        """Rollback to a previous checkpoint"""
        if checkpoint_id not in self.checkpoint_history:
            return False
        
        checkpoint = self.checkpoint_history[checkpoint_id]
        self.shared_context = checkpoint["shared_context"].copy()
        self.agent_outputs = checkpoint["agent_outputs"].copy()
        self.completed_agents = checkpoint["completed_agents"].copy()
        return True
    
    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary"""
        return {
            "execution_id": self.execution_id,
            "status": self.status.value,
            "total_agents_completed": len(self.completed_agents),
            "total_agents_failed": len(self.failed_agents),
            "total_agents_pending": len(self.pending_agents),
            "completed_agents": self.completed_agents,
            "failed_agents": self.failed_agents,
            "pending_agents": self.pending_agents,
            "logs_count": len(self.execution_logs),
            "checkpoints": list(self.checkpoint_history.keys()),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization"""
        return {
            "execution_id": self.execution_id,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "shared_context": self.shared_context,
            "agent_outputs": self.agent_outputs,
            "agent_errors": self.agent_errors,
            "completed_agents": self.completed_agents,
            "pending_agents": self.pending_agents,
            "failed_agents": self.failed_agents,
            "logs": [log.to_dict() for log in self.execution_logs],
            "metadata": self.metadata,
        }
