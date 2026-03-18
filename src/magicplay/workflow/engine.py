"""
Intelligent Workflow Engine for MagicPlay.

Key features:
1. Quality-driven generation with automatic retry
2. Resource caching and reuse
3. Cost optimization through intelligent model selection
4. Parallel processing for efficiency
5. Progress tracking and failure recovery
"""
import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ..evaluator.base import BaseEvaluator, EvaluationResult, QualityLevel
from ..resource_registry.registry import ResourceRegistry, ResourceRecord, ResourceType, ResourceState


class WorkflowStep(Enum):
    """Steps in the video generation workflow."""
    STORY_PLANNING = "story_planning"          # Story bible and plot generation
    CHARACTER_DESIGN = "character_design"      # Character descriptions and anchors
    SCENE_DESIGN = "scene_design"              # Scene concepts and layouts
    SCRIPT_GENERATION = "script_generation"    # Dialogue and action scripts
    IMAGE_GENERATION = "image_generation"      # Character and scene images
    VIDEO_GENERATION = "video_generation"      # Video clips from images
    AUDIO_GENERATION = "audio_generation"      # Narration and sound effects
    FINAL_ASSEMBLY = "final_assembly"          # Final video assembly


class WorkflowState(Enum):
    """State of a workflow."""
    PENDING = "pending"          # Workflow created but not started
    RUNNING = "running"          # Workflow in progress
    PAUSED = "paused"            # Workflow paused
    COMPLETED = "completed"      # Workflow completed successfully
    FAILED = "failed"            # Workflow failed
    CANCELLED = "cancelled"      # Workflow cancelled by user


class GenerationStrategy(Enum):
    """Strategy for resource generation."""
    QUALITY_FIRST = "quality_first"      # Maximize quality, accept higher cost
    BALANCED = "balanced"                # Balance quality and cost
    COST_OPTIMIZED = "cost_optimized"    # Minimize cost, accept lower quality
    CACHE_ONLY = "cache_only"            # Use cached resources only


@dataclass
class GenerationRequest:
    """Request for generating a resource."""
    step: WorkflowStep
    resource_type: ResourceType
    parameters: Dict[str, Any]
    metadata: Dict[str, Any]
    strategy: GenerationStrategy = GenerationStrategy.BALANCED
    max_attempts: int = 3
    min_quality_threshold: float = 60.0
    max_cost_limit: Optional[float] = None
    parent_workflow_id: Optional[str] = None


@dataclass
class GenerationResult:
    """Result of a generation attempt."""
    request: GenerationRequest
    resource_record: Optional[ResourceRecord]
    evaluation_result: Optional[EvaluationResult]
    attempts: int
    total_cost: float
    total_time: float
    success: bool
    error_message: Optional[str] = None
    
    @property
    def quality_score(self) -> float:
        """Get quality score from evaluation."""
        if self.evaluation_result:
            return self.evaluation_result.score
        return 0.0
    
    @property
    def is_acceptable(self) -> bool:
        """Check if quality is acceptable."""
        if self.evaluation_result:
            return self.evaluation_result.is_acceptable
        return False


class WorkflowNode(ABC):
    """Base class for workflow nodes (steps)."""
    
    def __init__(
        self,
        step: WorkflowStep,
        name: str,
        description: str = "",
        required_inputs: Optional[List[str]] = None,
        produces_outputs: Optional[List[str]] = None,
    ):
        self.step = step
        self.name = name
        self.description = description
        self.required_inputs = required_inputs or []
        self.produces_outputs = produces_outputs or []
        self.evaluator: Optional[BaseEvaluator] = None
        self.max_attempts = 3
        self.retry_delay = 1.0  # seconds
    
    @abstractmethod
    async def execute(
        self,
        context: Dict[str, Any],
        request: GenerationRequest,
        registry: ResourceRegistry,
    ) -> GenerationResult:
        """Execute the workflow step."""
        pass
    
    def set_evaluator(self, evaluator: BaseEvaluator):
        """Set quality evaluator for this node."""
        self.evaluator = evaluator
    
    def _evaluate_quality(
        self, 
        input_data: Union[str, Path, Any], 
        **kwargs
    ) -> Optional[EvaluationResult]:
        """Evaluate quality using configured evaluator."""
        if not self.evaluator:
            return None
        
        try:
            return self.evaluator.evaluate(input_data, **kwargs)
        except Exception as e:
            logging.warning(f"Quality evaluation failed: {e}")
            return None


class WorkflowEngine:
    """
    Intelligent workflow engine for managing video generation.
    
    Features:
    - Parallel step execution
    - Quality-driven retry logic
    - Resource caching and reuse
    - Cost tracking and optimization
    - Progress monitoring
    """
    
    def __init__(
        self,
        registry: Optional[ResourceRegistry] = None,
        default_strategy: GenerationStrategy = GenerationStrategy.BALANCED,
        max_parallel_tasks: int = 3,
        enable_caching: bool = True,
        enable_quality_check: bool = True,
    ):
        self.registry = registry or ResourceRegistry()
        self.default_strategy = default_strategy
        self.max_parallel_tasks = max_parallel_tasks
        self.enable_caching = enable_caching
        self.enable_quality_check = enable_quality_check
        self.nodes: Dict[WorkflowStep, WorkflowNode] = {}
        self.evaluators: Dict[ResourceType, BaseEvaluator] = {}
        self.workflow_states: Dict[str, WorkflowState] = {}
        self.workflow_results: Dict[str, List[GenerationResult]] = {}
        
        # Performance tracking
        self.total_cost = 0.0
        self.total_generations = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    def register_node(self, node: WorkflowNode):
        """Register a workflow node."""
        self.nodes[node.step] = node
    
    def register_evaluator(self, resource_type: ResourceType, evaluator: BaseEvaluator):
        """Register a quality evaluator for a resource type."""
        self.evaluators[resource_type] = evaluator
        
        # Assign evaluator to relevant nodes
        for node in self.nodes.values():
            # Simple heuristic: assign evaluator based on resource type
            if hasattr(node, 'resource_type') and node.resource_type == resource_type:
                node.set_evaluator(evaluator)
    
    def start_workflow(self, workflow_id: str):
        """Start a new workflow."""
        self.workflow_states[workflow_id] = WorkflowState.RUNNING
        self.workflow_results[workflow_id] = []
        self.logger.info(f"Started workflow: {workflow_id}")
    
    def complete_workflow(self, workflow_id: str):
        """Mark workflow as completed."""
        self.workflow_states[workflow_id] = WorkflowState.COMPLETED
        self.logger.info(f"Completed workflow: {workflow_id}")
    
    def fail_workflow(self, workflow_id: str, error: str):
        """Mark workflow as failed."""
        self.workflow_states[workflow_id] = WorkflowState.FAILED
        self.logger.error(f"Workflow {workflow_id} failed: {error}")
    
    def get_workflow_state(self, workflow_id: str) -> WorkflowState:
        """Get current state of a workflow."""
        return self.workflow_states.get(workflow_id, WorkflowState.PENDING)
    
    def get_workflow_results(self, workflow_id: str) -> List[GenerationResult]:
        """Get results for a workflow."""
        return self.workflow_results.get(workflow_id, [])
    
    async def execute_step(
        self,
        workflow_id: str,
        step: WorkflowStep,
        parameters: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        strategy: Optional[GenerationStrategy] = None,
        max_attempts: Optional[int] = None,
        min_quality_threshold: Optional[float] = None,
    ) -> GenerationResult:
        """Execute a single workflow step."""
        if workflow_id not in self.workflow_states:
            self.start_workflow(workflow_id)
        
        if self.workflow_states[workflow_id] != WorkflowState.RUNNING:
            return GenerationResult(
                request=None,
                resource_record=None,
                evaluation_result=None,
                attempts=0,
                total_cost=0.0,
                total_time=0.0,
                success=False,
                error_message=f"Workflow is not running: {self.workflow_states[workflow_id]}",
            )
        
        # Get the workflow node
        node = self.nodes.get(step)
        if not node:
            return GenerationResult(
                request=None,
                resource_record=None,
                evaluation_result=None,
                attempts=0,
                total_cost=0.0,
                total_time=0.0,
                success=False,
                error_message=f"No node registered for step: {step}",
            )
        
        # Create generation request
        resource_type = self._infer_resource_type(step)
        request = GenerationRequest(
            step=step,
            resource_type=resource_type,
            parameters=parameters,
            metadata=metadata or {},
            strategy=strategy or self.default_strategy,
            max_attempts=max_attempts or node.max_attempts,
            min_quality_threshold=min_quality_threshold or 60.0,
            parent_workflow_id=workflow_id,
        )
        
        # Execute the step
        start_time = time.time()
        result = await self._execute_with_strategy(
            workflow_id, node, request, parameters
        )
        end_time = time.time()
        
        # Update result timing
        result.total_time = end_time - start_time
        
        # Record result
        self.workflow_results[workflow_id].append(result)
        
        # Update statistics
        if result.success:
            self.total_cost += result.total_cost
            self.total_generations += 1
        
        return result
    
    async def _execute_with_strategy(
        self,
        workflow_id: str,
        node: WorkflowNode,
        request: GenerationRequest,
        context: Dict[str, Any],
    ) -> GenerationResult:
        """Execute generation with strategy-based optimization."""
        
        # Step 1: Check cache if enabled
        cached_result = None
        if self.enable_caching:
            cached_result = await self._try_cache_lookup(request)
            if cached_result and cached_result.success:
                self.cache_hits += 1
                self.logger.info(f"Cache hit for {request.step.value}")
                return cached_result
        
        self.cache_misses += 1
        
        # Step 2: Execute based on strategy
        strategy = request.strategy
        attempts = 0
        total_cost = 0.0
        best_result: Optional[GenerationResult] = None
        
        while attempts < request.max_attempts:
            attempts += 1
            self.logger.info(f"Attempt {attempts}/{request.max_attempts} for {request.step.value}")
            
            # Execute generation
            result = await node.execute(context, request, self.registry)
            result.attempts = attempts
            
            # Track cost
            if result.resource_record:
                total_cost += result.resource_record.generation_cost
            
            # Evaluate quality if enabled
            if self.enable_quality_check and result.resource_record:
                evaluator = self.evaluators.get(request.resource_type)
                if evaluator and result.resource_record.storage_path:
                    eval_result = evaluator.evaluate(result.resource_record.storage_path)
                    result.evaluation_result = eval_result
            
            # Check if result meets requirements
            meets_quality = (
                result.evaluation_result and 
                result.evaluation_result.score >= request.min_quality_threshold
            )
            
            meets_cost = (
                request.max_cost_limit is None or
                total_cost <= request.max_cost_limit
            )
            
            # Strategy-specific success conditions
            success = False
            if strategy == GenerationStrategy.QUALITY_FIRST:
                success = meets_quality
            elif strategy == GenerationStrategy.COST_OPTIMIZED:
                success = meets_cost and (
                    result.evaluation_result is None or
                    result.evaluation_result.quality_level != QualityLevel.UNUSABLE
                )
            elif strategy == GenerationStrategy.CACHE_ONLY:
                success = cached_result is not None
            else:  # BALANCED
                success = meets_quality and meets_cost
            
            # Update best result
            if not best_result or (
                result.evaluation_result and 
                result.evaluation_result.score > (best_result.evaluation_result.score if best_result.evaluation_result else 0)
            ):
                best_result = result
            
            # If successful, return
            if success:
                result.success = True
                result.total_cost = total_cost
                
                # Register in cache
                if result.resource_record and self.enable_caching:
                    await self._register_in_cache(request, result.resource_record)
                
                return result
            
            # Wait before retry
            if attempts < request.max_attempts:
                await asyncio.sleep(node.retry_delay)
        
        # Return best attempt if all failed
        if best_result:
            best_result.success = False
            best_result.total_cost = total_cost
            best_result.error_message = f"Failed to meet requirements after {attempts} attempts"
            return best_result
        
        # Complete failure
        return GenerationResult(
            request=request,
            resource_record=None,
            evaluation_result=None,
            attempts=attempts,
            total_cost=total_cost,
            total_time=0.0,
            success=False,
            error_message="All generation attempts failed",
        )
    
    async def _try_cache_lookup(self, request: GenerationRequest) -> Optional[GenerationResult]:
        """Try to find suitable cached resource."""
        try:
            # Search for similar resources
            similar = self.registry.find_similar(
                resource_type=request.resource_type,
                metadata=request.metadata,
                min_quality=request.min_quality_threshold,
                max_results=1,
            )
            
            if similar:
                resource = similar[0]
                
                # Check if resource meets strategy requirements
                meets_strategy = True
                if request.strategy == GenerationStrategy.QUALITY_FIRST:
                    meets_strategy = resource.quality_score >= 80.0
                elif request.strategy == GenerationStrategy.BALANCED:
                    meets_strategy = resource.quality_score >= 60.0
                
                if meets_strategy:
                    # Create evaluation result
                    eval_result = None
                    if self.enable_quality_check:
                        evaluator = self.evaluators.get(request.resource_type)
                        if evaluator and resource.storage_path:
                            eval_result = evaluator.evaluate(resource.storage_path)
                    
                    return GenerationResult(
                        request=request,
                        resource_record=resource,
                        evaluation_result=eval_result,
                        attempts=0,
                        total_cost=0.0,  # Cache hit has no cost
                        total_time=0.0,
                        success=True,
                    )
        
        except Exception as e:
            self.logger.warning(f"Cache lookup failed: {e}")
        
        return None
    
    async def _register_in_cache(
        self, 
        request: GenerationRequest, 
        resource_record: ResourceRecord
    ):
        """Register generated resource in cache."""
        try:
            # Read content if available
            content = None
            if resource_record.storage_path and resource_record.storage_path.exists():
                with open(resource_record.storage_path, 'rb') as f:
                    content = f.read()
            
            # Update registry
            self.registry.register(
                resource_type=request.resource_type,
                content=content,
                storage_path=resource_record.storage_path,
                metadata=request.metadata,
                quality_score=resource_record.quality_score,
                generation_cost=resource_record.generation_cost,
                state=resource_record.state,
                tags=[f"workflow:{request.parent_workflow_id}", f"step:{request.step.value}"],
            )
            
        except Exception as e:
            self.logger.warning(f"Cache registration failed: {e}")
    
    def _infer_resource_type(self, step: WorkflowStep) -> ResourceType:
        """Infer resource type from workflow step."""
        mapping = {
            WorkflowStep.CHARACTER_DESIGN: ResourceType.CHARACTER_IMAGE,
            WorkflowStep.SCENE_DESIGN: ResourceType.SCENE_CONCEPT,
            WorkflowStep.SCRIPT_GENERATION: ResourceType.SCRIPT,
            WorkflowStep.IMAGE_GENERATION: ResourceType.CHARACTER_IMAGE,  # Could be either
            WorkflowStep.VIDEO_GENERATION: ResourceType.VIDEO_CLIP,
            WorkflowStep.AUDIO_GENERATION: ResourceType.AUDIO,
            WorkflowStep.STORY_PLANNING: ResourceType.STORY_BIBLE,
        }
        
        return mapping.get(step, ResourceType.PROMPT)
    
    async def execute_workflow(
        self,
        workflow_id: str,
        steps: List[Tuple[WorkflowStep, Dict[str, Any]]],
        parallel: bool = True,
    ) -> List[GenerationResult]:
        """Execute a complete workflow with multiple steps."""
        self.start_workflow(workflow_id)
        
        results = []
        
        if parallel and len(steps) > 1:
            # Execute steps in parallel with limited concurrency
            semaphore = asyncio.Semaphore(self.max_parallel_tasks)
            
            async def execute_with_semaphore(step_data):
                async with semaphore:
                    step, params = step_data
                    return await self.execute_step(
                        workflow_id=workflow_id,
                        step=step,
                        parameters=params,
                    )
            
            tasks = [execute_with_semaphore(step_data) for step_data in steps]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions
            filtered_results = []
            for result in results:
                if isinstance(result, Exception):
                    self.logger.error(f"Step execution failed: {result}")
                else:
                    filtered_results.append(result)
            results = filtered_results
            
        else:
            # Execute steps sequentially
            for step, params in steps:
                result = await self.execute_step(
                    workflow_id=workflow_id,
                    step=step,
                    parameters=params,
                )
                results.append(result)
                
                # Stop if step failed and workflow should stop
                if not result.success:
                    self.fail_workflow(workflow_id, result.error_message or "Step failed")
                    break
        
        # Check if all steps succeeded
        if all(r.success for r in results):
            self.complete_workflow(workflow_id)
        elif self.get_workflow_state(workflow_id) == WorkflowState.RUNNING:
            self.fail_workflow(workflow_id, "Some steps failed")
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "total_cost": self.total_cost,
            "total_generations": self.total_generations,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": (
                self.cache_hits / (self.cache_hits + self.cache_misses) 
                if (self.cache_hits + self.cache_misses) > 0 else 0.0
            ),
            "active_workflows": sum(
                1 for state in self.workflow_states.values() 
                if state == WorkflowState.RUNNING
            ),
            "completed_workflows": sum(
                1 for state in self.workflow_states.values() 
                if state == WorkflowState.COMPLETED
            ),
            "registered_nodes": len(self.nodes),
            "registered_evaluators": len(self.evaluators),
        }
    
    def reset_statistics(self):
        """Reset engine statistics."""
        self.total_cost = 0.0
        self.total_generations = 0
        self.cache_hits = 0
        self.cache_misses = 0
    
    async def cleanup(self, max_age_days: int = 30):
        """Clean up old resources and workflows."""
        if self.registry:
            deleted = self.registry.cleanup(max_age_days=max_age_days)
            self.logger.info(f"Cleaned up {deleted} old resources")
        
        # Clean up completed workflows older than max_age_days
        # (Implementation depends on workflow storage mechanism)
        return deleted if self.registry else 0


# Factory function for easy engine creation
def create_workflow_engine(
    registry: Optional[ResourceRegistry] = None,
    strategy: GenerationStrategy = GenerationStrategy.BALANCED,
    parallel_tasks: int = 3,
    enable_cache: bool = True,
    enable_quality: bool = True,
) -> WorkflowEngine:
    """Create and configure a workflow engine."""
    engine = WorkflowEngine(
        registry=registry,
        default_strategy=strategy,
        max_parallel_tasks=parallel_tasks,
        enable_caching=enable_cache,
        enable_quality_check=enable_quality,
    )
    
    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    
    return engine