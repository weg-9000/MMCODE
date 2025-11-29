"""
ThreatAnalyzer - Task Orchestration Capability
==============================================

Advanced task orchestration for coordinating security testing workflows,
managing task dependencies, and optimizing execution sequences.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from ....security.models import (
    TaskNode,
    PentestPhase,
    RiskLevel,
    SecurityFinding,
    generate_task_id
)

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task execution priority levels"""
    CRITICAL = "critical"
    HIGH = "high" 
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


@dataclass
class TaskDependency:
    """Task dependency relationship"""
    task_id: str
    depends_on: List[str]
    dependency_type: str  # "sequential", "parallel", "conditional"
    condition: Optional[str] = None


@dataclass 
class ExecutionPlan:
    """Task execution plan with scheduling"""
    plan_id: str
    tasks: List[TaskNode]
    dependencies: List[TaskDependency]
    estimated_duration_seconds: int
    parallel_groups: List[List[str]] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TaskOrchestrationCapability:
    """
    Advanced task orchestration and workflow management
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._active_executions: Dict[str, Dict[str, Any]] = {}
        self._task_registry: Dict[str, TaskNode] = {}
        
    async def create_execution_plan(self,
                                  tasks: List[TaskNode],
                                  objectives: List[str],
                                  constraints: Dict[str, Any] = None) -> ExecutionPlan:
        """
        Create optimized execution plan for tasks
        
        Args:
            tasks: List of tasks to orchestrate
            objectives: Testing objectives
            constraints: Resource and time constraints
            
        Returns:
            ExecutionPlan with optimized task scheduling
        """
        constraints = constraints or {}
        self.logger.info(f"Creating execution plan for {len(tasks)} tasks")
        
        # Analyze task dependencies
        dependencies = self._analyze_task_dependencies(tasks)
        
        # Calculate parallel execution groups
        parallel_groups = self._identify_parallel_groups(tasks, dependencies)
        
        # Generate execution order
        execution_order = self._calculate_execution_order(tasks, dependencies)
        
        # Estimate total duration
        estimated_duration = self._estimate_total_duration(tasks, parallel_groups)
        
        plan = ExecutionPlan(
            plan_id=f"plan_{generate_task_id()}",
            tasks=tasks,
            dependencies=dependencies,
            estimated_duration_seconds=estimated_duration,
            parallel_groups=parallel_groups,
            execution_order=execution_order
        )
        
        # Optimize plan if needed
        if constraints.get("max_duration_hours"):
            plan = self._optimize_for_time_constraint(plan, constraints["max_duration_hours"])
        
        return plan
    
    async def execute_plan(self,
                          plan: ExecutionPlan,
                          executor_callback,
                          progress_callback = None) -> Dict[str, Any]:
        """
        Execute task plan with orchestration
        
        Args:
            plan: Execution plan to run
            executor_callback: Function to execute individual tasks
            progress_callback: Optional progress reporting callback
            
        Returns:
            Execution results summary
        """
        self.logger.info(f"Executing plan: {plan.plan_id}")
        
        execution_id = f"exec_{plan.plan_id}"
        self._active_executions[execution_id] = {
            "plan": plan,
            "start_time": datetime.now(timezone.utc),
            "completed_tasks": set(),
            "failed_tasks": set(),
            "running_tasks": set(),
            "results": {}
        }
        
        try:
            # Execute tasks according to plan
            for group in plan.parallel_groups:
                # Execute parallel group
                group_tasks = await self._execute_parallel_group(
                    group, plan, executor_callback, execution_id
                )
                
                # Update progress
                if progress_callback:
                    progress = len(self._active_executions[execution_id]["completed_tasks"]) / len(plan.tasks)
                    await progress_callback(progress, group_tasks)
            
            # Generate execution summary
            execution = self._active_executions[execution_id]
            end_time = datetime.now(timezone.utc)
            
            return {
                "execution_id": execution_id,
                "plan_id": plan.plan_id,
                "start_time": execution["start_time"].isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": (end_time - execution["start_time"]).total_seconds(),
                "total_tasks": len(plan.tasks),
                "completed_tasks": len(execution["completed_tasks"]),
                "failed_tasks": len(execution["failed_tasks"]),
                "success_rate": len(execution["completed_tasks"]) / len(plan.tasks),
                "results": execution["results"]
            }
            
        finally:
            # Cleanup
            if execution_id in self._active_executions:
                del self._active_executions[execution_id]
    
    def optimize_task_sequence(self,
                             tasks: List[TaskNode],
                             optimization_target: str = "time") -> List[TaskNode]:
        """
        Optimize task sequence for specific target
        
        Args:
            tasks: Tasks to optimize
            optimization_target: "time", "risk", "information_gain"
            
        Returns:
            Optimized task sequence
        """
        if optimization_target == "time":
            return self._optimize_for_time(tasks)
        elif optimization_target == "risk":
            return self._optimize_for_risk(tasks)
        elif optimization_target == "information_gain":
            return self._optimize_for_information_gain(tasks)
        else:
            return tasks
    
    def calculate_critical_path(self,
                              tasks: List[TaskNode],
                              dependencies: List[TaskDependency]) -> List[str]:
        """
        Calculate critical path through task dependencies
        
        Args:
            tasks: List of tasks
            dependencies: Task dependencies
            
        Returns:
            List of task IDs in critical path
        """
        # Build dependency graph
        task_map = {t.id: t for t in tasks}
        dep_graph = {dep.task_id: dep.depends_on for dep in dependencies}
        
        # Calculate longest path (critical path)
        def calculate_path_duration(task_id: str, visited: Set[str]) -> int:
            if task_id in visited:
                return 0  # Cycle detection
            
            visited.add(task_id)
            task = task_map.get(task_id)
            if not task:
                return 0
            
            max_dep_duration = 0
            for dep_id in dep_graph.get(task_id, []):
                dep_duration = calculate_path_duration(dep_id, visited.copy())
                max_dep_duration = max(max_dep_duration, dep_duration)
            
            return max_dep_duration + task.estimated_duration_seconds
        
        # Find task with longest total path
        critical_tasks = []
        max_duration = 0
        
        for task in tasks:
            total_duration = calculate_path_duration(task.id, set())
            if total_duration > max_duration:
                max_duration = total_duration
                # Reconstruct critical path
                critical_tasks = self._reconstruct_critical_path(task.id, dep_graph, task_map)
        
        return critical_tasks
    
    def suggest_task_parallelization(self,
                                   tasks: List[TaskNode]) -> List[List[str]]:
        """
        Suggest task parallelization opportunities
        
        Args:
            tasks: Tasks to analyze for parallelization
            
        Returns:
            List of parallel task groups (task IDs)
        """
        # Group tasks by phase and independence
        phase_groups = {}
        for task in tasks:
            phase = task.phase
            if phase not in phase_groups:
                phase_groups[phase] = []
            phase_groups[phase].append(task.id)
        
        parallel_groups = []
        
        # Within each phase, identify independent tasks
        for phase, task_ids in phase_groups.items():
            phase_tasks = [t for t in tasks if t.id in task_ids]
            independent_groups = self._find_independent_task_groups(phase_tasks)
            parallel_groups.extend(independent_groups)
        
        return parallel_groups
    
    def _analyze_task_dependencies(self, tasks: List[TaskNode]) -> List[TaskDependency]:
        """Analyze dependencies between tasks"""
        dependencies = []
        task_by_id = {t.id: t for t in tasks}
        
        for task in tasks:
            deps = []
            
            # Phase dependencies
            current_phase_index = self._get_phase_index(task.phase)
            for other_task in tasks:
                other_phase_index = self._get_phase_index(other_task.phase)
                if other_phase_index < current_phase_index:
                    deps.append(other_task.id)
            
            # Explicit dependencies (if task has parent/children relationships)
            if hasattr(task, 'parent_id') and task.parent_id:
                deps.append(task.parent_id)
            
            if deps:
                dependencies.append(TaskDependency(
                    task_id=task.id,
                    depends_on=deps,
                    dependency_type="sequential"
                ))
        
        return dependencies
    
    def _identify_parallel_groups(self,
                                tasks: List[TaskNode], 
                                dependencies: List[TaskDependency]) -> List[List[str]]:
        """Identify tasks that can run in parallel"""
        # Build dependency map
        dep_map = {dep.task_id: set(dep.depends_on) for dep in dependencies}
        
        # Group tasks by their dependency depth
        groups = []
        remaining_tasks = set(t.id for t in tasks)
        
        while remaining_tasks:
            # Find tasks with no remaining dependencies
            ready_tasks = []
            for task_id in remaining_tasks:
                task_deps = dep_map.get(task_id, set())
                if not task_deps.intersection(remaining_tasks):
                    ready_tasks.append(task_id)
            
            if ready_tasks:
                groups.append(ready_tasks)
                remaining_tasks -= set(ready_tasks)
            else:
                # Handle circular dependencies
                self.logger.warning("Possible circular dependency detected")
                groups.append(list(remaining_tasks))
                break
        
        return groups
    
    def _calculate_execution_order(self,
                                 tasks: List[TaskNode],
                                 dependencies: List[TaskDependency]) -> List[str]:
        """Calculate optimal execution order"""
        # Topological sort with priority consideration
        dep_map = {dep.task_id: dep.depends_on for dep in dependencies}
        task_map = {t.id: t for t in tasks}
        
        order = []
        remaining = set(t.id for t in tasks)
        
        while remaining:
            # Find ready tasks (no outstanding dependencies)
            ready = []
            for task_id in remaining:
                deps = dep_map.get(task_id, [])
                if not any(dep in remaining for dep in deps):
                    ready.append(task_id)
            
            if not ready:
                # Handle circular dependencies
                ready = [remaining.pop()]
            
            # Sort ready tasks by priority
            ready.sort(key=lambda tid: task_map[tid].priority_score, reverse=True)
            
            order.extend(ready)
            remaining -= set(ready)
        
        return order
    
    def _estimate_total_duration(self,
                               tasks: List[TaskNode],
                               parallel_groups: List[List[str]]) -> int:
        """Estimate total execution duration considering parallelization"""
        task_map = {t.id: t for t in tasks}
        total_duration = 0
        
        for group in parallel_groups:
            # Duration of parallel group is the maximum duration in the group
            group_duration = max(
                task_map[task_id].estimated_duration_seconds 
                for task_id in group
            )
            total_duration += group_duration
        
        return total_duration
    
    async def _execute_parallel_group(self,
                                    group: List[str],
                                    plan: ExecutionPlan,
                                    executor_callback,
                                    execution_id: str) -> Dict[str, Any]:
        """Execute a group of parallel tasks"""
        task_map = {t.id: t for t in plan.tasks}
        execution = self._active_executions[execution_id]
        
        # Create async tasks for parallel execution
        async_tasks = []
        for task_id in group:
            task = task_map[task_id]
            execution["running_tasks"].add(task_id)
            async_task = asyncio.create_task(
                self._execute_single_task(task, executor_callback, execution_id)
            )
            async_tasks.append((task_id, async_task))
        
        # Wait for all tasks to complete
        results = {}
        for task_id, async_task in async_tasks:
            try:
                result = await async_task
                results[task_id] = result
                execution["completed_tasks"].add(task_id)
                execution["results"][task_id] = result
            except Exception as e:
                self.logger.error(f"Task {task_id} failed: {e}")
                execution["failed_tasks"].add(task_id)
                results[task_id] = {"error": str(e)}
            finally:
                execution["running_tasks"].discard(task_id)
        
        return results
    
    async def _execute_single_task(self,
                                 task: TaskNode,
                                 executor_callback,
                                 execution_id: str) -> Dict[str, Any]:
        """Execute a single task"""
        self.logger.debug(f"Executing task: {task.id} - {task.name}")
        
        try:
            start_time = datetime.now(timezone.utc)
            result = await executor_callback(task)
            end_time = datetime.now(timezone.utc)
            
            return {
                "task_id": task.id,
                "status": "completed",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": (end_time - start_time).total_seconds(),
                "result": result
            }
        except Exception as e:
            return {
                "task_id": task.id,
                "status": "failed",
                "error": str(e)
            }
    
    def _optimize_for_time_constraint(self,
                                    plan: ExecutionPlan,
                                    max_hours: int) -> ExecutionPlan:
        """Optimize plan to fit within time constraint"""
        max_seconds = max_hours * 3600
        
        if plan.estimated_duration_seconds <= max_seconds:
            return plan
        
        # Remove or deprioritize low-priority tasks
        task_map = {t.id: t for t in plan.tasks}
        sorted_tasks = sorted(plan.tasks, key=lambda t: t.priority_score, reverse=True)
        
        optimized_tasks = []
        current_duration = 0
        
        for task in sorted_tasks:
            if current_duration + task.estimated_duration_seconds <= max_seconds:
                optimized_tasks.append(task)
                current_duration += task.estimated_duration_seconds
        
        # Recreate plan with optimized tasks
        dependencies = [dep for dep in plan.dependencies if dep.task_id in [t.id for t in optimized_tasks]]
        parallel_groups = self._identify_parallel_groups(optimized_tasks, dependencies)
        
        plan.tasks = optimized_tasks
        plan.dependencies = dependencies
        plan.parallel_groups = parallel_groups
        plan.estimated_duration_seconds = current_duration
        
        return plan
    
    def _optimize_for_time(self, tasks: List[TaskNode]) -> List[TaskNode]:
        """Optimize task sequence for minimum execution time"""
        return sorted(tasks, key=lambda t: t.estimated_duration_seconds)
    
    def _optimize_for_risk(self, tasks: List[TaskNode]) -> List[TaskNode]:
        """Optimize task sequence to minimize risk"""
        risk_order = {
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2, 
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4
        }
        return sorted(tasks, key=lambda t: risk_order.get(t.risk_level, 0))
    
    def _optimize_for_information_gain(self, tasks: List[TaskNode]) -> List[TaskNode]:
        """Optimize task sequence for maximum information gain"""
        return sorted(tasks, key=lambda t: t.priority_score, reverse=True)
    
    def _get_phase_index(self, phase: PentestPhase) -> int:
        """Get numeric index for phase ordering"""
        phase_order = [
            PentestPhase.RECONNAISSANCE,
            PentestPhase.SCANNING,
            PentestPhase.ENUMERATION,
            PentestPhase.VULNERABILITY_ASSESSMENT,
            PentestPhase.EXPLOITATION,
            PentestPhase.POST_EXPLOITATION,
            PentestPhase.REPORTING,
        ]
        try:
            return phase_order.index(phase)
        except ValueError:
            return 0
    
    def _find_independent_task_groups(self, tasks: List[TaskNode]) -> List[List[str]]:
        """Find groups of independent tasks within a phase"""
        # Simple heuristic: group by tool or target
        groups = {}
        
        for task in tasks:
            # Group by tool requirement
            tool = task.tool_required or "manual"
            if tool not in groups:
                groups[tool] = []
            groups[tool].append(task.id)
        
        return [group for group in groups.values() if len(group) > 1]
    
    def _reconstruct_critical_path(self,
                                 end_task_id: str,
                                 dep_graph: Dict[str, List[str]],
                                 task_map: Dict[str, TaskNode]) -> List[str]:
        """Reconstruct critical path from end task"""
        path = []
        current = end_task_id
        visited = set()
        
        while current and current not in visited:
            path.append(current)
            visited.add(current)
            
            # Find dependency with longest duration
            deps = dep_graph.get(current, [])
            if deps:
                longest_dep = max(deps, key=lambda dep_id: task_map.get(dep_id, TaskNode()).estimated_duration_seconds)
                current = longest_dep
            else:
                break
        
        return list(reversed(path))