"""Tests for orchestration system"""

import asyncio
import pytest
from typing import Dict, Any

from orchestrator import Orchestrator, OrchestrationState
from orchestrator.config import OrchestratorConfig, ExecutionMode
from orchestrator.orchestrator import Agent
from orchestrator.state import ExecutionStatus


class MockAgent(Agent):
    """Mock agent for testing"""
    
    def __init__(self, name: str, delay: float = 0.1, should_fail: bool = False):
        super().__init__(name)
        self.delay = delay
        self.should_fail = should_fail
        self.executed = False
    
    async def execute(self, state: OrchestrationState) -> Dict[str, Any]:
        """Mock execution"""
        self.executed = True
        await asyncio.sleep(self.delay)
        
        if self.should_fail:
            raise Exception(f"Mock failure in {self.name}")
        
        return {
            "agent": self.name,
            "status": "completed",
            "data": f"Output from {self.name}",
        }


class TestOrchestratorCore:
    """Test core orchestrator functionality"""
    
    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self):
        """Test orchestrator initialization"""
        config = OrchestratorConfig()
        orchestrator = Orchestrator(config)
        
        assert orchestrator.config == config
        assert len(orchestrator.agents) == 0
        assert orchestrator.get_status() == ExecutionStatus.PENDING.value
    
    @pytest.mark.asyncio
    async def test_register_agent(self):
        """Test agent registration"""
        orchestrator = Orchestrator(OrchestratorConfig())
        agent = MockAgent("test_agent")
        
        orchestrator.register_agent(agent)
        
        assert "test_agent" in orchestrator.agents
        assert orchestrator.agents["test_agent"] == agent
    
    @pytest.mark.asyncio
    async def test_register_multiple_agents(self):
        """Test registering multiple agents"""
        orchestrator = Orchestrator(OrchestratorConfig())
        agents = [
            MockAgent("agent1"),
            MockAgent("agent2"),
            MockAgent("agent3"),
        ]
        
        orchestrator.register_agents(agents)
        
        assert len(orchestrator.agents) == 3
        for agent in agents:
            assert agent.get_name() in orchestrator.agents
    
    @pytest.mark.asyncio
    async def test_set_workflow(self):
        """Test workflow configuration"""
        orchestrator = Orchestrator(OrchestratorConfig())
        agents = [MockAgent(f"agent{i}") for i in range(3)]
        orchestrator.register_agents(agents)
        
        workflow = [agent.get_name() for agent in agents]
        orchestrator.set_workflow(workflow)
        
        assert orchestrator.workflow_steps == workflow
    
    @pytest.mark.asyncio
    async def test_set_invalid_workflow(self):
        """Test workflow with unregistered agent"""
        orchestrator = Orchestrator(OrchestratorConfig())
        orchestrator.register_agent(MockAgent("agent1"))
        
        with pytest.raises(ValueError):
            orchestrator.set_workflow(["agent1", "nonexistent_agent"])
    
    @pytest.mark.asyncio
    async def test_sequential_execution(self):
        """Test sequential agent execution"""
        config = OrchestratorConfig(mode=ExecutionMode.SEQUENTIAL)
        orchestrator = Orchestrator(config)
        
        agents = [
            MockAgent("planner"),
            MockAgent("developer"),
            MockAgent("tester"),
        ]
        orchestrator.register_agents(agents)
        orchestrator.set_workflow([a.get_name() for a in agents])
        
        state = await orchestrator.execute()
        
        assert state.status == ExecutionStatus.COMPLETED
        assert len(state.completed_agents) == 3
        assert all(agent.executed for agent in agents)
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test parallel agent execution"""
        config = OrchestratorConfig(mode=ExecutionMode.PARALLEL)
        orchestrator = Orchestrator(config)
        
        agents = [
            MockAgent("agent1", delay=0.1),
            MockAgent("agent2", delay=0.1),
            MockAgent("agent3", delay=0.1),
        ]
        orchestrator.register_agents(agents)
        orchestrator.set_workflow([a.get_name() for a in agents])
        
        import time
        start = time.time()
        state = await orchestrator.execute()
        elapsed = time.time() - start
        
        assert state.status == ExecutionStatus.COMPLETED
        assert len(state.completed_agents) == 3
        # Parallel execution should be faster than sequential
        assert elapsed < 1.0  # 3 agents * 0.1s delay should be ~0.1s in parallel
    
    @pytest.mark.asyncio
    async def test_agent_failure_handling(self):
        """Test failure handling"""
        config = OrchestratorConfig(
            mode=ExecutionMode.SEQUENTIAL,
            max_retries=2,
        )
        orchestrator = Orchestrator(config)
        
        agents = [
            MockAgent("agent1"),
            MockAgent("agent2", should_fail=True),
            MockAgent("agent3"),
        ]
        orchestrator.register_agents(agents)
        orchestrator.set_workflow([a.get_name() for a in agents])
        
        state = await orchestrator.execute()
        
        assert "agent2" in state.failed_agents
        assert state.status == ExecutionStatus.FAILED
        # Should have retry logs
        assert len([log for log in state.execution_logs if log.agent_name == "agent2"]) > 1
    
    @pytest.mark.asyncio
    async def test_shared_state_context(self):
        """Test shared context between agents"""
        orchestrator = Orchestrator(OrchestratorConfig())
        
        class ContextAwareAgent(Agent):
            async def execute(self, state: OrchestrationState) -> Dict[str, Any]:
                # Read from context
                previous = state.get_context("previous_output", "none")
                # Write to context
                state.update_context(f"output_{self.name}", f"processed {previous}")
                return {"context": previous}
        
        agents = [
            ContextAwareAgent("agent1"),
            ContextAwareAgent("agent2"),
        ]
        orchestrator.register_agents(agents)
        orchestrator.set_workflow([a.get_name() for a in agents])
        
        # Set initial context
        config = OrchestratorConfig()
        orchestrator.config = config
        
        state = await orchestrator.execute()
        
        assert "output_agent1" in state.shared_context
        assert "output_agent2" in state.shared_context
    
    @pytest.mark.asyncio
    async def test_callbacks(self):
        """Test callback execution"""
        orchestrator = Orchestrator(OrchestratorConfig())
        
        callback_calls = {"on_start": 0, "on_complete": 0}
        
        def on_start_callback(state):
            callback_calls["on_start"] += 1
        
        def on_complete_callback(state):
            callback_calls["on_complete"] += 1
        
        orchestrator.add_callback("on_start", on_start_callback)
        orchestrator.add_callback("on_complete", on_complete_callback)
        
        agents = [MockAgent("test")]
        orchestrator.register_agents(agents)
        orchestrator.set_workflow(["test"])
        
        state = await orchestrator.execute()
        
        assert callback_calls["on_start"] == 1
        assert callback_calls["on_complete"] == 1
    
    @pytest.mark.asyncio
    async def test_state_checkpoint_and_rollback(self):
        """Test state checkpoint and rollback"""
        state = OrchestrationState(execution_id="test")
        
        # Set initial context
        state.update_context("key1", "value1")
        state.update_context("key2", "value2")
        
        # Create checkpoint
        state.create_checkpoint("checkpoint1")
        
        # Modify state
        state.update_context("key1", "modified")
        state.update_context("key3", "value3")
        
        # Rollback
        success = state.rollback_to_checkpoint("checkpoint1")
        
        assert success
        assert state.get_context("key1") == "value1"
        assert state.get_context("key2") == "value2"
        assert "key3" not in state.shared_context
    
    @pytest.mark.asyncio
    async def test_execution_logs(self):
        """Test execution logging"""
        orchestrator = Orchestrator(OrchestratorConfig())
        agents = [MockAgent("agent1")]
        orchestrator.register_agents(agents)
        orchestrator.set_workflow(["agent1"])
        
        state = await orchestrator.execute()
        
        assert len(state.execution_logs) > 0
        log = state.execution_logs[0]
        assert log.agent_name == "agent1"
        assert log.status == ExecutionStatus.COMPLETED
        assert log.output_data is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
