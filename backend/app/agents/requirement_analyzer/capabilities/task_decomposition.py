"""Task Decomposition Engine for A2A Coordination"""

import uuid
import logging
from typing import Dict, Any, List
from datetime import datetime

from ..models.analysis_models import (
    AnalysisResult, CoordinationPlan, AgentTask, TaskType, 
    AgentRole, Priority
)


class TaskDecompositionEngine:
    """
    Engine for decomposing analysis results into coordinated A2A tasks
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Task estimation rules (in seconds)
        self.task_estimates = {
            TaskType.ARCHITECTURE_DESIGN: 120,
            TaskType.STACK_RECOMMENDATION: 90,
            TaskType.DOCUMENT_GENERATION: 150,
            TaskType.QUALITY_EVALUATION: 60
        }
    
    async def decompose(self, analysis: AnalysisResult) -> CoordinationPlan:
        """
        Decompose analysis result into coordinated agent tasks
        """
        self.logger.info("Starting task decomposition")
        
        plan_id = str(uuid.uuid4())
        tasks = []
        
        # Create base context from analysis
        base_context = {
            "analysis": analysis.to_dict(),
            "requirements_complexity": analysis.complexity_score,
            "domain": analysis.domain
        }
        
        # Task 1: Architecture Design (depends on analysis only)
        arch_task = AgentTask(
            task_id=str(uuid.uuid4()),
            task_type=TaskType.ARCHITECTURE_DESIGN,
            agent_role=AgentRole.ARCHITECT,
            context=base_context.copy(),
            priority=self._determine_priority(analysis, "architecture"),
            estimated_duration=self.task_estimates[TaskType.ARCHITECTURE_DESIGN]
        )
        tasks.append(arch_task)
        
        # Task 2: Stack Recommendation (depends on architecture)
        stack_context = base_context.copy()
        stack_task = AgentTask(
            task_id=str(uuid.uuid4()),
            task_type=TaskType.STACK_RECOMMENDATION,
            agent_role=AgentRole.RECOMMENDER,
            dependencies=[arch_task.task_id],
            context=stack_context,
            priority=self._determine_priority(analysis, "stack"),
            estimated_duration=self.task_estimates[TaskType.STACK_RECOMMENDATION]
        )
        tasks.append(stack_task)
        
        # Task 3: Document Generation (depends on both architecture and stack)
        doc_context = base_context.copy()
        doc_task = AgentTask(
            task_id=str(uuid.uuid4()),
            task_type=TaskType.DOCUMENT_GENERATION,
            agent_role=AgentRole.DOCUMENTER,
            dependencies=[arch_task.task_id, stack_task.task_id],
            context=doc_context,
            priority=self._determine_priority(analysis, "documentation"),
            estimated_duration=self.task_estimates[TaskType.DOCUMENT_GENERATION]
        )
        tasks.append(doc_task)
        
        # Create execution order (considering dependencies)
        execution_order = self._create_execution_order(tasks)
        
        # Calculate total estimated duration
        total_duration = self._calculate_total_duration(tasks, execution_order)
        
        plan = CoordinationPlan(
            plan_id=plan_id,
            tasks=tasks,
            execution_order=execution_order,
            total_estimated_duration=total_duration
        )
        
        self.logger.info(f"Task decomposition completed: {len(tasks)} tasks, {total_duration}s estimated")
        return plan
    
    def _determine_priority(self, analysis: AnalysisResult, task_area: str) -> Priority:
        """
        Determine task priority based on analysis results
        """
        # High priority for complex systems
        if analysis.complexity_score > 0.7:
            return Priority.HIGH
        
        # Check for specific quality attributes that affect priority
        quality_attrs = [qa.get('name', '') for qa in analysis.quality_attributes]
        
        if task_area == "architecture":
            if any(attr in quality_attrs for attr in ['scalability', 'performance', 'security']):
                return Priority.HIGH
        elif task_area == "stack":
            if any(attr in quality_attrs for attr in ['performance', 'compatibility']):
                return Priority.HIGH
        elif task_area == "documentation":
            if any(attr in quality_attrs for attr in ['compliance', 'maintainability']):
                return Priority.HIGH
        
        # Check for specific constraints that increase priority
        constraints = [c.get('type', '') for c in analysis.constraints]
        if any(constraint in constraints for constraint in ['time', 'compliance']):
            return Priority.HIGH
        
        return Priority.MEDIUM
    
    def _create_execution_order(self, tasks: List[AgentTask]) -> List[List[str]]:
        """
        Create execution order considering task dependencies
        """
        # Build dependency graph
        task_map = {task.task_id: task for task in tasks}
        execution_groups = []
        completed_tasks = set()
        
        while len(completed_tasks) < len(tasks):
            # Find tasks that can be executed (all dependencies satisfied)
            ready_tasks = []
            for task in tasks:
                if task.task_id not in completed_tasks:
                    if all(dep in completed_tasks for dep in task.dependencies):
                        ready_tasks.append(task.task_id)
            
            if not ready_tasks:
                # Circular dependency or other issue
                remaining_tasks = [t.task_id for t in tasks if t.task_id not in completed_tasks]
                self.logger.warning(f"Potential circular dependency. Adding remaining tasks: {remaining_tasks}")
                execution_groups.append(remaining_tasks)
                break
            
            execution_groups.append(ready_tasks)
            completed_tasks.update(ready_tasks)
        
        return execution_groups
    
    def _calculate_total_duration(self, 
                                 tasks: List[AgentTask], 
                                 execution_order: List[List[str]]) -> int:
        """
        Calculate total estimated execution time considering parallel execution
        """
        task_map = {task.task_id: task for task in tasks}
        total_duration = 0
        
        for group in execution_order:
            # Tasks in the same group execute in parallel
            # Total time for group is the maximum duration of tasks in the group
            group_duration = 0
            for task_id in group:
                task = task_map[task_id]
                group_duration = max(group_duration, task.estimated_duration)
            
            total_duration += group_duration
        
        return total_duration