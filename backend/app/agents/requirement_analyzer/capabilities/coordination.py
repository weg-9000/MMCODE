"""Agent Coordination Engine for A2A Orchestration"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from ...shared.a2a_client.client import A2AClient
from ...shared.models.a2a_models import A2ATask, TaskStatus
from ..models.analysis_models import CoordinationPlan, OrchestrationResult


class AgentCoordinator:
    """
    Engine for coordinating multiple agents through A2A protocol
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.parallel_execution = config.get("parallel_execution", True)
        self.task_timeout = config.get("task_timeout", 180)
        
    async def execute_plan(self, 
                          plan: CoordinationPlan,
                          agent_endpoints: Dict[str, str],
                          a2a_client: A2AClient) -> Dict[str, Any]:
        """
        Execute coordination plan by orchestrating agent tasks
        """
        self.logger.info(f"Executing coordination plan {plan.plan_id}")
        
        start_time = datetime.utcnow()
        result = OrchestrationResult(plan_id=plan.plan_id)
        
        try:
            # Execute tasks according to plan
            if self.parallel_execution:
                await self._execute_parallel(plan, agent_endpoints, a2a_client, result)
            else:
                await self._execute_sequential(plan, agent_endpoints, a2a_client, result)
            
            # Calculate execution time
            result.total_execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Determine overall status
            if result.failed_tasks:
                if len(result.failed_tasks) >= len(plan.tasks):
                    result.status = "failed"
                else:
                    result.status = "partial"
            else:
                result.status = "completed"
            
            # Calculate overall quality score
            result.overall_quality_score = self._calculate_quality_score(result)
            
            self.logger.info(f"Orchestration completed: {result.status}, quality: {result.overall_quality_score}")
            return result.to_dict()
            
        except Exception as e:
            self.logger.error(f"Orchestration failed for plan {plan.plan_id}: {e}")
            result.status = "failed"
            result.total_execution_time = (datetime.utcnow() - start_time).total_seconds()
            return result.to_dict()
    
    async def _execute_parallel(self, 
                               plan: CoordinationPlan,
                               agent_endpoints: Dict[str, str],
                               a2a_client: A2AClient,
                               result: OrchestrationResult):
        """
        Execute tasks in parallel groups according to dependency order
        """
        task_map = {task.task_id: task for task in plan.tasks}
        task_results = {}
        
        for group in plan.execution_order:
            self.logger.info(f"Executing parallel group: {group}")
            
            # Create tasks for this group
            group_tasks = []
            for task_id in group:
                task = task_map[task_id]
                
                # Build context with results from dependencies
                enhanced_context = task.context.copy()
                for dep_id in task.dependencies:
                    if dep_id in task_results:
                        dep_result = task_results[dep_id]
                        if dep_result and dep_result.status == TaskStatus.COMPLETED:
                            # Add dependency result to context
                            enhanced_context[f"dependency_{dep_id}"] = dep_result.result
                            if hasattr(dep_result, 'artifact') and dep_result.artifact:
                                enhanced_context[f"artifact_{dep_id}"] = dep_result.artifact
                
                # Create async task for agent execution
                group_tasks.append(
                    self._execute_agent_task(task, enhanced_context, agent_endpoints, a2a_client)
                )
            
            # Execute group tasks in parallel
            group_results = await asyncio.gather(*group_tasks, return_exceptions=True)
            
            # Process results
            for i, task_result in enumerate(group_results):
                task_id = group[i]
                
                if isinstance(task_result, Exception):
                    self.logger.error(f"Task {task_id} failed: {task_result}")
                    result.failed_tasks.append(task_id)
                else:
                    result.executed_tasks.append(task_id)
                    task_results[task_id] = task_result
                    
                    # Store artifact if available
                    if hasattr(task_result, 'result') and task_result.result:
                        if 'artifact_id' in task_result.result:
                            artifact_id = task_result.result['artifact_id']
                            result.artifacts[artifact_id] = task_result.result
    
    async def _execute_sequential(self,
                                 plan: CoordinationPlan,
                                 agent_endpoints: Dict[str, str], 
                                 a2a_client: A2AClient,
                                 result: OrchestrationResult):
        """
        Execute tasks sequentially (fallback mode)
        """
        task_map = {task.task_id: task for task in plan.tasks}
        task_results = {}
        
        # Flatten execution order for sequential processing
        all_tasks = []
        for group in plan.execution_order:
            all_tasks.extend(group)
        
        for task_id in all_tasks:
            task = task_map[task_id]
            
            try:
                # Build context with dependency results
                enhanced_context = task.context.copy()
                for dep_id in task.dependencies:
                    if dep_id in task_results:
                        dep_result = task_results[dep_id]
                        enhanced_context[f"dependency_{dep_id}"] = dep_result.result
                
                # Execute task
                task_result = await self._execute_agent_task(
                    task, enhanced_context, agent_endpoints, a2a_client
                )
                
                result.executed_tasks.append(task_id)
                task_results[task_id] = task_result
                
                # Store artifact
                if hasattr(task_result, 'result') and task_result.result:
                    if 'artifact_id' in task_result.result:
                        artifact_id = task_result.result['artifact_id']
                        result.artifacts[artifact_id] = task_result.result
                        
            except Exception as e:
                self.logger.error(f"Task {task_id} failed: {e}")
                result.failed_tasks.append(task_id)
    
    async def _execute_agent_task(self,
                                 task,
                                 context: Dict[str, Any],
                                 agent_endpoints: Dict[str, str],
                                 a2a_client: A2AClient) -> A2ATask:
        """
        Execute a single agent task via A2A protocol
        """
        # Determine target agent
        agent_name = self._get_agent_name_for_task(task)
        
        if agent_name not in agent_endpoints:
            raise ValueError(f"No endpoint configured for agent: {agent_name}")
        
        agent_url = agent_endpoints[agent_name]
        
        self.logger.info(f"Executing task {task.task_id} on agent {agent_name}")
        
        try:
            # Create and wait for task completion
            a2a_task = await a2a_client.create_task_with_wait(
                agent_url=agent_url,
                task_type=task.task_type.value,
                context=context,
                max_wait_time=self.task_timeout
            )
            
            if a2a_task.status == TaskStatus.COMPLETED:
                self.logger.info(f"Task {task.task_id} completed successfully")
            else:
                self.logger.warning(f"Task {task.task_id} completed with status: {a2a_task.status}")
            
            return a2a_task
            
        except Exception as e:
            self.logger.error(f"Task execution failed for {task.task_id}: {e}")
            raise
    
    def _get_agent_name_for_task(self, task) -> str:
        """
        Map agent role to agent name for endpoint lookup
        """
        role_to_agent = {
            "architect": "architect",
            "recommender": "stack_recommender", 
            "documenter": "documenter"
        }
        
        agent_role = task.agent_role.value if hasattr(task.agent_role, 'value') else str(task.agent_role)
        return role_to_agent.get(agent_role, agent_role)
    
    def _calculate_quality_score(self, result: OrchestrationResult) -> float:
        """
        Calculate overall quality score from orchestration results
        """
        if not result.executed_tasks:
            return 0.0
        
        # Base score from completion rate
        completion_rate = len(result.executed_tasks) / (len(result.executed_tasks) + len(result.failed_tasks))
        
        # Quality scores from artifacts
        artifact_qualities = []
        for artifact in result.artifacts.values():
            if isinstance(artifact, dict) and 'quality_score' in artifact:
                artifact_qualities.append(artifact['quality_score'])
        
        if artifact_qualities:
            avg_artifact_quality = sum(artifact_qualities) / len(artifact_qualities)
            return (completion_rate * 0.6) + (avg_artifact_quality * 0.4)
        else:
            return completion_rate