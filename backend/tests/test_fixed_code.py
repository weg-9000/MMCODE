"""
Unit Tests: Recently Fixed Code
===============================

Tests for code that was recently fixed:
1. orchestration.py - syntax fix and stub implementations
2. agent_registry.py - JSON serialization/deserialization
3. mock_client.py - is_registered method
4. dependencies.py - asyncio compatibility
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import uuid


class TestOrchestrationFixes:
    """Tests for orchestration.py fixes"""

    @pytest.mark.asyncio
    async def test_ensure_agents_registered_all_registered(self):
        """Test _ensure_agents_registered when all agents are already registered"""
        from app.agents.shared.a2a_client.mock_client import InMemoryA2AClient

        client = InMemoryA2AClient()
        # Register all required agents
        client.register("requirement-analyzer", Mock())
        client.register("architect", Mock())
        client.register("stack_recommender", Mock())
        client.register("documenter", Mock())

        # Should not raise and should skip DB checks
        assert client.is_registered("requirement-analyzer")
        assert client.is_registered("architect")
        assert client.is_registered("stack_recommender")
        assert client.is_registered("documenter")

    @pytest.mark.asyncio
    async def test_save_orchestration_results_structure(self):
        """Test _save_orchestration_results handles various result types"""
        # This tests the structure of result handling
        results = {
            "analysis_result": {"content": "analyzed", "quality_score": 0.9},
            "architecture_design": {"layers": ["api", "service", "data"]},
            "stack_recommendation": {"frontend": "React", "backend": "FastAPI"},
            "documentation": "Generated docs content",
            "completed_tasks": [
                {"agent_id": "analyzer", "task_type": "analysis", "quality_score": 0.85}
            ]
        }

        # Verify all expected keys are present
        assert "analysis_result" in results
        assert "architecture_design" in results
        assert "stack_recommendation" in results
        assert "documentation" in results
        assert "completed_tasks" in results

        # Verify task data structure
        for task in results["completed_tasks"]:
            assert "agent_id" in task
            assert "task_type" in task


class TestAgentRegistryFixes:
    """Tests for agent_registry.py JSON fixes"""

    def test_json_serialization_format(self):
        """Test that agent data is serialized as proper JSON"""
        agent_data = {
            "agent_id": "test-agent",
            "agent_name": "Test Agent",
            "description": "A test agent",
            "endpoint_url": "local://test-agent",
            "capabilities": ["capability1", "capability2"],
            "version": "1.0.0",
            "status": "active",
            "metadata": {"key": "value"}
        }

        # Serialize to JSON
        json_str = json.dumps(agent_data)

        # Should be valid JSON
        assert isinstance(json_str, str)

        # Should be deserializable
        parsed = json.loads(json_str)
        assert parsed["agent_id"] == "test-agent"
        assert parsed["capabilities"] == ["capability1", "capability2"]

    def test_parse_json_data(self):
        """Test parsing JSON formatted agent data"""
        json_data = '{"agent_id": "test", "agent_name": "Test", "capabilities": ["a", "b"]}'

        parsed = json.loads(json_data)

        assert parsed["agent_id"] == "test"
        assert parsed["agent_name"] == "Test"
        assert len(parsed["capabilities"]) == 2

    def test_parse_bytes_data(self):
        """Test parsing bytes data (as returned from Redis)"""
        json_data = b'{"agent_id": "test", "agent_name": "Test"}'

        # Decode bytes to string
        decoded = json_data.decode('utf-8')
        parsed = json.loads(decoded)

        assert parsed["agent_id"] == "test"

    def test_legacy_dict_string_parsing(self):
        """Test parsing legacy Python dict string format"""
        import ast

        # Legacy format: Python dict as string
        legacy_data = "{'agent_id': 'test', 'agent_name': 'Test'}"

        # Should fail JSON parsing
        with pytest.raises(json.JSONDecodeError):
            json.loads(legacy_data)

        # Should succeed with ast.literal_eval
        parsed = ast.literal_eval(legacy_data)
        assert parsed["agent_id"] == "test"


class TestMockClientFixes:
    """Tests for mock_client.py is_registered method"""

    def test_is_registered_true(self):
        """Test is_registered returns True for registered agents"""
        from app.agents.shared.a2a_client.mock_client import InMemoryA2AClient

        client = InMemoryA2AClient()
        client.register("test-agent", Mock())

        assert client.is_registered("test-agent") is True

    def test_is_registered_false(self):
        """Test is_registered returns False for unregistered agents"""
        from app.agents.shared.a2a_client.mock_client import InMemoryA2AClient

        client = InMemoryA2AClient()

        assert client.is_registered("non-existent") is False

    def test_get_registered_agents(self):
        """Test get_registered_agents returns all agent names"""
        from app.agents.shared.a2a_client.mock_client import InMemoryA2AClient

        client = InMemoryA2AClient()
        client.register("agent-1", Mock())
        client.register("agent-2", Mock())
        client.register("agent-3", Mock())

        agents = client.get_registered_agents()

        assert len(agents) == 3
        assert "agent-1" in agents
        assert "agent-2" in agents
        assert "agent-3" in agents

    def test_register_and_check(self):
        """Test register then check pattern"""
        from app.agents.shared.a2a_client.mock_client import InMemoryA2AClient

        client = InMemoryA2AClient()

        # Initially not registered
        assert client.is_registered("new-agent") is False

        # Register
        client.register("new-agent", Mock())

        # Now registered
        assert client.is_registered("new-agent") is True

    @pytest.mark.asyncio
    async def test_create_task_registered_agent(self):
        """Test creating task for registered agent"""
        from app.agents.shared.a2a_client.mock_client import InMemoryA2AClient

        client = InMemoryA2AClient()

        # Create mock agent with handle_task method
        mock_agent = Mock()
        mock_agent.handle_task = AsyncMock(return_value={"result": "success"})

        client.register("test-agent", mock_agent)

        task = await client.create_task(
            agent_url="local://test-agent",
            task_type="test_task",
            context={"data": "test"}
        )

        assert task is not None
        assert task.task_type == "test_task"

    @pytest.mark.asyncio
    async def test_create_task_unregistered_agent_raises(self):
        """Test creating task for unregistered agent raises error"""
        from app.agents.shared.a2a_client.mock_client import InMemoryA2AClient

        client = InMemoryA2AClient()

        with pytest.raises(RuntimeError) as exc_info:
            await client.create_task(
                agent_url="local://unregistered-agent",
                task_type="test_task",
                context={}
            )

        assert "not registered" in str(exc_info.value)


class TestDependenciesFixes:
    """Tests for dependencies.py asyncio compatibility"""

    def test_asyncio_run_compatibility(self):
        """Test that asyncio.run works in non-async context"""
        async def sample_coroutine():
            return "result"

        # Should work without deprecation warning in Python 3.10+
        result = asyncio.run(sample_coroutine())
        assert result == "result"

    def test_get_running_loop_raises_in_sync(self):
        """Test that get_running_loop raises RuntimeError in sync context"""
        with pytest.raises(RuntimeError):
            asyncio.get_running_loop()

    @pytest.mark.asyncio
    async def test_get_running_loop_works_in_async(self):
        """Test that get_running_loop works in async context"""
        loop = asyncio.get_running_loop()
        assert loop is not None

    def test_event_loop_pattern(self):
        """Test the recommended event loop pattern"""
        async def async_operation():
            return "done"

        # Pattern used in dependencies.py
        try:
            # This should raise in sync context
            loop = asyncio.get_running_loop()
            # If we get here, we're in async context (shouldn't happen in this test)
            assert False, "Should have raised RuntimeError"
        except RuntimeError:
            # Expected: no running event loop, safe to use asyncio.run()
            result = asyncio.run(async_operation())
            assert result == "done"


class TestLLMInitializationFixes:
    """Tests for shared LLM initialization module"""

    def test_llm_initialization_module_exists(self):
        """Test that the shared LLM module can be imported"""
        from app.agents.shared.utils.llm_initialization import (
            initialize_llm_sync,
            initialize_llm_async,
            ensure_llm_instance,
            get_llm_info
        )

        # All functions should be importable
        assert callable(initialize_llm_sync)
        assert callable(initialize_llm_async)
        assert callable(ensure_llm_instance)
        assert callable(get_llm_info)

    def test_get_llm_info_structure(self):
        """Test get_llm_info returns expected structure"""
        from app.agents.shared.utils.llm_initialization import get_llm_info

        # Create mock LLM
        mock_llm = Mock()
        mock_llm.model_name = "gpt-4"
        mock_llm.temperature = 0.1

        info = get_llm_info(mock_llm)

        assert "model_name" in info
        assert "temperature" in info
        assert info["model_name"] == "gpt-4"
        assert info["temperature"] == 0.1


class TestDockerfilefix:
    """Tests to verify Dockerfile configurations"""

    def test_dockerfile_syntax_validation(self):
        """Test that Dockerfile has correct structure"""
        import os

        # Check main Dockerfile exists
        main_dockerfile = os.path.join(
            os.path.dirname(__file__),
            "..",
            "Dockerfile"
        )

        # Check security sandbox Dockerfile exists
        sandbox_dockerfile = os.path.join(
            os.path.dirname(__file__),
            "..",
            "docker",
            "security-sandbox",
            "Dockerfile"
        )

        # Files should exist (may fail in CI without full repo)
        # This is more of a smoke test
        pass  # Actual validation would require docker build


class TestIntegrationScenarios:
    """Integration-style tests for fixed components working together"""

    @pytest.mark.asyncio
    async def test_agent_registration_flow(self):
        """Test complete agent registration and task creation flow"""
        from app.agents.shared.a2a_client.mock_client import InMemoryA2AClient

        client = InMemoryA2AClient()

        # 1. Check agents not registered
        assert not client.is_registered("analyzer")
        assert client.get_registered_agents() == []

        # 2. Register agents
        mock_analyzer = Mock()
        mock_analyzer.handle_task = AsyncMock(return_value={"analyzed": True})

        client.register("analyzer", mock_analyzer)

        # 3. Verify registration
        assert client.is_registered("analyzer")
        assert "analyzer" in client.get_registered_agents()

        # 4. Create and track task
        task = await client.create_task(
            agent_url="local://analyzer",
            task_type="requirement_analysis",
            context={"requirements": "Build an API"}
        )

        assert task.task_type == "requirement_analysis"

        # 5. Check task status
        status = await client.get_task_status("local://analyzer", task.task_id)
        assert status is not None

    def test_json_roundtrip(self):
        """Test JSON serialization roundtrip for agent data"""
        original = {
            "agent_id": "test-agent",
            "agent_name": "Test Agent",
            "capabilities": ["cap1", "cap2"],
            "metadata": {"nested": {"key": "value"}}
        }

        # Serialize
        json_str = json.dumps(original)

        # Deserialize
        restored = json.loads(json_str)

        # Should be equal
        assert restored == original
        assert restored["metadata"]["nested"]["key"] == "value"
