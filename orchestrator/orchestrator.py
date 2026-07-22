"""Core Orchestrator for Multi-Agent System"""

import logging
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime
import asyncio
from abc import ABC, abstractmethod
import uuid

from .config import OrchestratorConfig, ExecutionMode
from .state import OrchestrationState, ExecutionStatus, ExecutionLog


logger = logging.getLogger(__name__)


class Agent(ABC):
    """Base Agent interface"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def execute(self, state: OrchestrationState) -> Dict[str, Any]:
        """Execute agent's task"""
        pass
    
    def get_name(self) -> str:
        """Get agent name"""
        return self.name


class Orchestrator:
    """Core orchestrator for managing multiple agents"""
    
    def __init__(self, config: OrchestratorConfig):
        """Initialize orchestrator
        
        Args:
            config: Orchestrator configuration
        """
        self.config = config
        self.state: Optional[OrchestrationState] = None
        self.agents: Dict[str, Agent] = {}
        self.workflow_steps: List[str] = []  # Order of agent execution
        self.callbacks: Dict[str, List[Callable]] = {
            "on_start": [],
            "on_agent_start": [],
            "on_agent_complete": [],
            "on_agent_error": [],
            "on_complete": [],
        }
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Setup logging"""
        if self.config.enable_logging:
            logging.basicConfig(level=self.config.log_level)
            logger.setLevel(self.config.log_level)
    
    def register_agent(self, agent: Agent) -> None:
        """Register an agent
        
        Args:
            agent: Agent to register
        """
        self.agents[agent.get_name()] = agent
        logger.info(f"Agent '{agent.get_name()}' registered")
    
    def register_agents(self, agents: List[Agent]) -> None:
        """Register multiple agents
        
        Args:
            agents: List of agents to register
        """
        for agent in agents:
            self.register_agent(agent)
    
    def set_workflow(self, steps: List[str]) -> None:
        """Set workflow execution order
        
        Args:
            steps: List of agent names in execution order
        """
        for step in steps:
            if step not in self.agents:
                raise ValueError(f"Agent '{step}' not registered")
        self.workflow_steps = steps
        logger.info(f"Workflow set: {' -> '.join(steps)}")
    
    def add_callback(self, event: str, callback: Callable) -> None:
        """Add callback for event
        
        Args:
            event: Event name (on_start, on_agent_complete, etc.)
            callback: Callback function
        """
        if event not in self.callbacks:
            raise ValueError(f"Unknown event: {event}")
        self.callbacks[event].append(callback)
    
    async def _execute_callback(self, event: str, *args, **kwargs) -> None:
        """Execute callbacks for event
        
        Args:
            event: Event name
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        for callback in self.callbacks[event]:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)
    
    async def _execute_agent(
        self,
        agent: Agent,
        retry_count: int = 0
    ) -> bool:
        """Execute single agent with error handling
        
        Args:
            agent: Agent to execute
            retry_count: Current retry attempt
        
        Returns:
            True if successful, False otherwise
        """
        agent_name = agent.get_name()
        logger.info(f"Starting agent: {agent_name}")
        
        await self._execute_callback("on_agent_start", agent_name, self.state)
        
        start_time = datetime.now()
        log = None
        
        try:
            # Execute agent
            output = await agent.execute(self.state)
            
            # Store output
            self.state.set_agent_output(agent_name, output)
            self.state.mark_agent_completed(agent_name)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # Create log
            log = ExecutionLog(
                agent_name=agent_name,
                status=ExecutionStatus.COMPLETED,
                timestamp=datetime.now(),
                input_data=self.state.shared_context.copy(),
                output_data=output,
                duration_seconds=duration,
            )
            self.state.add_log(log)
            
            logger.info(f"Agent '{agent_name}' completed in {duration:.2f}s")
            await self._execute_callback("on_agent_complete", agent_name, self.state, output)
            
            return True
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Agent '{agent_name}' failed: {error_message}")
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # Create error log
            log = ExecutionLog(
                agent_name=agent_name,
                status=ExecutionStatus.FAILED,
                timestamp=datetime.now(),
                input_data=self.state.shared_context.copy(),
                error_message=error_message,
                duration_seconds=duration,
            )
            self.state.add_log(log)
            
            # Retry logic
            if retry_count < self.config.max_retries:
                logger.info(f"Retrying agent '{agent_name}' (attempt {retry_count + 1}/{self.config.max_retries})")
                self.state.status = ExecutionStatus.RETRY
                return await self._execute_agent(agent, retry_count + 1)
            else:
                self.state.set_agent_error(agent_name, error_message)
                await self._execute_callback("on_agent_error", agent_name, self.state, error_message)
                return False
    
    async def _execute_sequential(self) -> None:
        """Execute agents sequentially"""
        logger.info("Starting sequential execution")
        
        for agent_name in self.workflow_steps:
            if self.state.status == ExecutionStatus.CANCELLED:
                break
            
            agent = self.agents[agent_name]
            success = await self._execute_agent(agent)
            
            if not success and not self.config.allow_agent_feedback:
                logger.error(f"Stopping execution due to agent failure: {agent_name}")
                break
    
    async def _execute_parallel(self) -> None:
        """Execute agents in parallel"""
        logger.info("Starting parallel execution")
        
        tasks = []
        for agent_name in self.workflow_steps:
            agent = self.agents[agent_name]
            tasks.append(self._execute_agent(agent))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle results
        for agent_name, result in zip(self.workflow_steps, results):
            if isinstance(result, Exception):
                logger.error(f"Agent '{agent_name}' raised exception: {result}")
    
    async def execute(self) -> OrchestrationState:
        """Execute orchestration workflow
        
        Returns:
            OrchestrationState with execution results
        """
        # Initialize state
        self.state = OrchestrationState(
            execution_id=str(uuid.uuid4()),
            pending_agents=self.workflow_steps.copy(),
        )
        self.state.status = ExecutionStatus.RUNNING
        self.state.start_time = datetime.now()
        
        logger.info(f"Starting orchestration: {self.state.execution_id}")
        await self._execute_callback("on_start", self.state)
        
        try:
            # Create initial checkpoint
            self.state.create_checkpoint("initial")
            
            # Execute based on mode
            if self.config.mode == ExecutionMode.SEQUENTIAL:
                await self._execute_sequential()
            elif self.config.mode == ExecutionMode.PARALLEL:
                await self._execute_parallel()
            else:
                # Hybrid mode - implement custom logic if needed
                await self._execute_sequential()
            
            # Determine final status
            if len(self.state.failed_agents) > 0:
                self.state.status = ExecutionStatus.FAILED
            else:
                self.state.status = ExecutionStatus.COMPLETED
            
        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            self.state.status = ExecutionStatus.FAILED
        
        finally:
            self.state.end_time = datetime.now()
            logger.info(
                f"Orchestration completed: {self.state.status.value} "
                f"(ID: {self.state.execution_id})"
            )
            await self._execute_callback("on_complete", self.state)
        
        return self.state
    
    def cancel(self) -> None:
        """Cancel ongoing orchestration"""
        if self.state and self.state.status == ExecutionStatus.RUNNING:
            self.state.status = ExecutionStatus.CANCELLED
            logger.info("Orchestration cancelled")
    
    def get_state(self) -> Optional[OrchestrationState]:
        """Get current orchestration state
        
        Returns:
            Current OrchestrationState or None
        """
        return self.state
    
    def get_status(self) -> str:
        """Get orchestration status
        
        Returns:
            Current status as string
        """
        if self.state:
            return self.state.status.value
        return ExecutionStatus.PENDING.value
