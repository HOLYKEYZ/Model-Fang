"""
Attack Orchestrator

Manages the execution of attack chains, multi-turn state tracking,
and structured logging. This is the central execution engine for
running adversarial attacks against target models.
"""

import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

from modelfang.schema.attack import AttackSchema, AttackStep, SuccessCondition
from modelfang.adapters.base import ModelAdapter, Message, ModelResponse
from modelfang.evaluator.base import Evaluator, EvaluationResult


class AttackStatus(Enum):
    """Status of an attack execution."""
    
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class StepResult:
    """
    Result of executing a single attack step.
    
    Attributes:
        step_id: ID of the executed step
        prompt: The prompt that was sent
        response: The model's response
        evaluation: Evaluation result from the evaluator
        timestamp: When the step was executed
        latency_ms: Response latency in milliseconds
        success: Whether the step was successful
        metadata: Additional metadata about the step
    """
    
    step_id: str
    prompt: str
    response: str
    evaluation: Optional[EvaluationResult] = None
    timestamp: str = ""
    latency_ms: float = 0.0
    success: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON logging."""
        return {
            "step_id": self.step_id,
            "prompt": self.prompt,
            "response": self.response,
            "evaluation": self.evaluation.to_dict() if self.evaluation else None,
            "timestamp": self.timestamp,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "metadata": self.metadata,
        }


@dataclass
class OrchestrationState:
    """
    Tracks the state of an attack orchestration.
    
    Attributes:
        attack_id: ID of the attack being executed
        status: Current status of the attack
        current_step_index: Index of the current step
        turn_count: Number of turns executed
        conversation_history: Full conversation history
        step_results: Results of each step executed
        start_time: When the attack started
        end_time: When the attack ended
        success_score: Cumulative success score (0.0 to 1.0)
        metadata: Additional state metadata
    """
    
    attack_id: str
    status: AttackStatus = AttackStatus.PENDING
    current_step_index: int = 0
    turn_count: int = 0
    conversation_history: List[Message] = field(default_factory=list)
    step_results: List[StepResult] = field(default_factory=list)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    success_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON output."""
        return {
            "attack_id": self.attack_id,
            "status": self.status.value,
            "current_step_index": self.current_step_index,
            "turn_count": self.turn_count,
            "conversation_history": [
                {"role": m.role, "content": m.content}
                for m in self.conversation_history
            ],
            "step_results": [r.to_dict() for r in self.step_results],
            "start_time": self.start_time,
            "end_time": self.end_time,
            "success_score": self.success_score,
            "metadata": self.metadata,
        }


class AttackOrchestrator:
    """
    Orchestrates the execution of attack chains against target models.
    
    Responsibilities:
    - Select and load attack chains from config
    - Manage multi-turn conversation state
    - Execute attack steps sequentially
    - Apply mutations deterministically when seeded
    - Evaluate responses using a separate evaluator
    - Emit structured JSON logs for every step
    - Stop when success threshold is met or max turns reached
    """
    
    def __init__(
        self,
        target_adapter: ModelAdapter,
        evaluator: Evaluator,
        seed: Optional[int] = None,
        max_turns: int = 20,
        success_threshold: float = 0.7,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the orchestrator.
        
        Args:
            target_adapter: Adapter for the target model
            evaluator: Evaluator for analyzing responses
            seed: Random seed for reproducibility
            max_turns: Maximum turns per attack
            success_threshold: Score threshold for attack success
            logger: Optional logger instance
        """
        self.target_adapter = target_adapter
        self.evaluator = evaluator
        self.seed = seed
        self.max_turns = max_turns
        self.success_threshold = success_threshold
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize random state for reproducibility
        if seed is not None:
            self.rng = random.Random(seed)
        else:
            self.rng = random.Random()
        
        # State tracking
        self._current_state: Optional[OrchestrationState] = None
        self._step_hooks: List[Callable[[StepResult], None]] = []
    
    def execute_attack(
        self,
        attack: AttackSchema,
        context: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
    ) -> OrchestrationState:
        """
        Execute a complete attack chain.
        
        Args:
            attack: The attack schema to execute
            context: Variables for prompt template rendering
            system_prompt: Optional system prompt for the target model
            
        Returns:
            OrchestrationState with the final state and results
        """
        context = context or {}
        
        # Initialize state
        self._current_state = OrchestrationState(
            attack_id=attack.attack_id,
            status=AttackStatus.RUNNING,
            start_time=datetime.utcnow().isoformat() + "Z",
        )
        
        self._log_event("attack_started", {
            "attack_id": attack.attack_id,
            "attack_name": attack.name,
            "category": attack.category.value,
            "severity": attack.severity.value,
            "step_count": len(attack.steps),
        })
        
        # Add system prompt to conversation if provided
        if system_prompt:
            self._current_state.conversation_history.append(
                Message(role="system", content=system_prompt)
            )
        
        try:
            # Execute each step
            for step_index, step in enumerate(attack.steps):
                self._current_state.current_step_index = step_index
                
                # Check if we've reached max turns
                if self._current_state.turn_count >= self.max_turns:
                    self._log_event("max_turns_reached", {
                        "turn_count": self._current_state.turn_count,
                        "max_turns": self.max_turns,
                    })
                    break
                
                # Execute the step
                step_result = self._execute_step(step, attack, context)
                self._current_state.step_results.append(step_result)
                
                # Call step hooks
                for hook in self._step_hooks:
                    hook(step_result)
                
                # Check for success
                if step_result.success:
                    self._current_state.success_score = max(
                        self._current_state.success_score,
                        step_result.evaluation.raw_score if step_result.evaluation else 0.5,
                    )
                
                # Check if success threshold reached
                if self._current_state.success_score >= self.success_threshold:
                    self._current_state.status = AttackStatus.SUCCESS
                    self._log_event("success_threshold_reached", {
                        "score": self._current_state.success_score,
                        "threshold": self.success_threshold,
                    })
                    break
            
            # Determine final status
            if self._current_state.status == AttackStatus.RUNNING:
                if self._current_state.success_score > 0:
                    self._current_state.status = AttackStatus.PARTIAL
                else:
                    self._current_state.status = AttackStatus.FAILED
        
        except Exception as e:
            self._current_state.status = AttackStatus.ABORTED
            self._current_state.metadata["error"] = str(e)
            self._log_event("attack_aborted", {"error": str(e)})
        
        finally:
            self._current_state.end_time = datetime.utcnow().isoformat() + "Z"
            self._log_event("attack_completed", {
                "status": self._current_state.status.value,
                "success_score": self._current_state.success_score,
                "turn_count": self._current_state.turn_count,
                "steps_executed": len(self._current_state.step_results),
            })
        
        return self._current_state
    
    def _execute_step(
        self,
        step: AttackStep,
        attack: AttackSchema,
        context: Dict[str, Any],
    ) -> StepResult:
        """
        Execute a single attack step.
        
        Args:
            step: The step to execute
            attack: The parent attack schema
            context: Variables for template rendering
            
        Returns:
            StepResult with the outcome
        """
        # Render the prompt
        try:
            prompt = step.render_prompt(context)
        except ValueError as e:
            return StepResult(
                step_id=step.step_id,
                prompt=step.prompt_template,
                response="",
                success=False,
                metadata={"error": f"Template rendering failed: {e}"},
            )
        
        self._log_event("step_started", {
            "step_id": step.step_id,
            "description": step.description,
        })
        
        # Add user message to conversation
        user_message = Message(role="user", content=prompt)
        self._current_state.conversation_history.append(user_message)
        
        # Send to target model
        start_time = time.time()
        try:
            response = self.target_adapter.send(
                messages=self._current_state.conversation_history,
            )
            latency_ms = (time.time() - start_time) * 1000
        except Exception as e:
            self._log_event("step_failed", {
                "step_id": step.step_id,
                "error": str(e),
            })
            return StepResult(
                step_id=step.step_id,
                prompt=prompt,
                response="",
                success=False,
                latency_ms=(time.time() - start_time) * 1000,
                metadata={"error": str(e)},
            )
        
        # Add assistant response to conversation
        assistant_message = Message(role="assistant", content=response.content)
        self._current_state.conversation_history.append(assistant_message)
        self._current_state.turn_count += 1
        
        # Evaluate the response
        evaluation = self.evaluator.evaluate(response.content, attack)
        
        # Determine success based on evaluation
        success = evaluation.raw_score >= self.success_threshold
        
        step_result = StepResult(
            step_id=step.step_id,
            prompt=prompt,
            response=response.content,
            evaluation=evaluation,
            latency_ms=latency_ms,
            success=success,
            metadata={
                "model": response.model,
                "finish_reason": response.finish_reason,
                "usage": response.usage,
            },
        )
        
        self._log_event("step_completed", {
            "step_id": step.step_id,
            "success": success,
            "evaluation_score": evaluation.raw_score,
            "latency_ms": latency_ms,
        })
        
        return step_result
    
    def add_step_hook(self, hook: Callable[[StepResult], None]) -> None:
        """
        Add a callback to be called after each step.
        
        Args:
            hook: Function that receives the StepResult
        """
        self._step_hooks.append(hook)
    
    def get_current_state(self) -> Optional[OrchestrationState]:
        """Get the current orchestration state."""
        return self._current_state
    
    def _log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Log a structured event.
        
        Args:
            event_type: Type of event
            data: Event data
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            **data,
        }
        self.logger.info(json.dumps(log_entry))
