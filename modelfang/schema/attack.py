"""
Attack Schema Layer

Defines structured attack definitions using dataclasses for type safety
and serialization support. All attacks are procedural chains with
explicit success conditions and reproducibility requirements.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class AttackCategory(Enum):
    """Categories of adversarial attacks against LLMs."""
    
    JAILBREAK = "jailbreak"
    INJECTION = "injection"
    EXFILTRATION = "exfiltration"
    TOOL_ABUSE = "tool_abuse"
    POLICY_EROSION = "policy_erosion"
    INSTRUCTION_OVERRIDE = "instruction_override"
    SYSTEM_PROMPT_LEAK = "system_prompt_leak"
    COMPLIANCE_DRIFT = "compliance_drift"


class Severity(Enum):
    """Severity levels for attacks based on potential impact."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    
    def to_numeric(self) -> int:
        """Convert severity to numeric value for scoring."""
        mapping = {
            Severity.LOW: 1,
            Severity.MEDIUM: 2,
            Severity.HIGH: 3,
            Severity.CRITICAL: 4,
        }
        return mapping[self]


class SuccessConditionType(Enum):
    """Types of success conditions for attack validation."""
    
    PATTERN_MATCH = "pattern_match"
    KEYWORD_PRESENCE = "keyword_presence"
    KEYWORD_ABSENCE = "keyword_absence"
    POLICY_LEAK = "policy_leak"
    INSTRUCTION_FOLLOWED = "instruction_followed"
    REFUSAL_BYPASS = "refusal_bypass"
    TONE_SHIFT = "tone_shift"
    CUSTOM_EVALUATOR = "custom_evaluator"


@dataclass
class SuccessCondition:
    """
    Defines when an attack step or chain is considered successful.
    
    Attributes:
        condition_type: The type of condition to check
        pattern: Regex pattern or keyword to match (if applicable)
        threshold: Numeric threshold for partial success (0.0 to 1.0)
        description: Human-readable description of the condition
        negate: If True, condition succeeds when pattern is NOT found
    """
    
    condition_type: SuccessConditionType
    pattern: Optional[str] = None
    threshold: float = 0.5
    description: str = ""
    negate: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON output."""
        return {
            "condition_type": self.condition_type.value,
            "pattern": self.pattern,
            "threshold": self.threshold,
            "description": self.description,
            "negate": self.negate,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SuccessCondition":
        """Deserialize from dictionary."""
        return cls(
            condition_type=SuccessConditionType(data["condition_type"]),
            pattern=data.get("pattern"),
            threshold=data.get("threshold", 0.5),
            description=data.get("description", ""),
            negate=data.get("negate", False),
        )


@dataclass
class TransitionRule:
    """
    Conditional transition rule for attack graph traversal.
    
    Attributes:
        target_states: List of evaluator states that trigger this rule
        min_confidence: Minimum evaluator confidence required
        max_turns: Optional turn limit for this transition
        next_step_id: ID of the step to transition to
    """
    
    target_states: List[str] # List of EvaluatorState values
    next_step_id: str
    min_confidence: float = 0.0
    max_turns: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_states": self.target_states,
            "next_step_id": self.next_step_id,
            "min_confidence": self.min_confidence,
            "max_turns": self.max_turns,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransitionRule":
        return cls(
            target_states=data.get("target_states", []),
            next_step_id=data["next_step_id"],
            min_confidence=data.get("min_confidence", 0.0),
            max_turns=data.get("max_turns"),
        )


@dataclass
class MutationPolicy:
    """
    Disciplined mutation policy for an attack step.
    
    Attributes:
        allowed_strategies: List of allowed mutation strategy names
        max_mutations: Maximum number of mutations allowed for this step
        escalation_order: Order to apply strategies (e.g. semantic -> persona)
        entropy_budget: Abstract budget for randomness/changes
    """
    
    allowed_strategies: List[str] = field(default_factory=lambda: ["semantic_reword"])
    max_mutations: int = 3
    escalation_order: List[str] = field(default_factory=list)
    entropy_budget: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed_strategies": self.allowed_strategies,
            "max_mutations": self.max_mutations,
            "escalation_order": self.escalation_order,
            "entropy_budget": self.entropy_budget,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MutationPolicy":
        return cls(
            allowed_strategies=data.get("allowed_strategies", ["semantic_reword"]),
            max_mutations=data.get("max_mutations", 3),
            escalation_order=data.get("escalation_order", []),
            entropy_budget=data.get("entropy_budget", 1.0),
        )


@dataclass
class AttackStep:
    """
    A single step in an attack chain.
    """
    
    step_id: str
    prompt_template: str
    description: str = ""
    expected_behavior: str = ""
    timeout_seconds: int = 30
    variables: Dict[str, Any] = field(default_factory=dict)
    success_conditions: List[SuccessCondition] = field(default_factory=list)
    transitions: List[TransitionRule] = field(default_factory=list)
    mutation_policy: Optional[MutationPolicy] = None
    
    def render_prompt(self, context: Dict[str, Any]) -> str:
        merged_vars = {**self.variables, **context}
        try:
            return self.prompt_template.format(**merged_vars)
        except KeyError as e:
            raise ValueError(f"Missing variable in prompt template: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "prompt_template": self.prompt_template,
            "description": self.description,
            "expected_behavior": self.expected_behavior,
            "timeout_seconds": self.timeout_seconds,
            "variables": self.variables,
            "success_conditions": [c.to_dict() for c in self.success_conditions],
            "transitions": [t.to_dict() for t in self.transitions],
            "mutation_policy": self.mutation_policy.to_dict() if self.mutation_policy else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AttackStep":
        conditions = [SuccessCondition.from_dict(c) for c in data.get("success_conditions", [])]
        transitions = [TransitionRule.from_dict(t) for t in data.get("transitions", [])]
        policy = MutationPolicy.from_dict(data["mutation_policy"]) if "mutation_policy" in data else None
        
        return cls(
            step_id=data["step_id"],
            prompt_template=data["prompt_template"],
            description=data.get("description", ""),
            expected_behavior=data.get("expected_behavior", ""),
            timeout_seconds=data.get("timeout_seconds", 30),
            variables=data.get("variables", {}),
            success_conditions=conditions,
            transitions=transitions,
            mutation_policy=policy,
        )


@dataclass
class AttackSchema:
    """
    Complete attack definition with metadata, steps, and success criteria.
    
    Attributes:
        attack_id: Unique identifier for this attack
        name: Human-readable name
        category: Attack category (jailbreak, injection, etc.)
        severity: Impact severity level
        description: Detailed description of the attack
        prerequisites: Required conditions before attack can execute
        steps: List of attack steps (graph nodes)
        start_step_id: ID of the starting step
        success_conditions: Overall conditions for attack success
        supported_model_types: List of model types this attack targets
        tags: Metadata tags for filtering/grouping
        author: Creator of the attack definition
        version: Schema version for compatibility
    """
    
    attack_id: str
    name: str
    category: AttackCategory
    severity: Severity
    description: str = ""
    prerequisites: List[str] = field(default_factory=list)
    steps: List[AttackStep] = field(default_factory=list)
    start_step_id: Optional[str] = None
    success_conditions: List[SuccessCondition] = field(default_factory=list)
    supported_model_types: List[str] = field(default_factory=lambda: ["*"])
    tags: List[str] = field(default_factory=list)
    author: str = "unknown"
    version: str = "1.0"
    
    def get_step_count(self) -> int:
        """Return the number of steps in this attack chain."""
        return len(self.steps)
    
    def get_step_by_id(self, step_id: str) -> Optional[AttackStep]:
        """Find a step by its ID."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None
    
    def get_start_step(self) -> Optional[AttackStep]:
        """Get the starting step."""
        if self.start_step_id:
            return self.get_step_by_id(self.start_step_id)
        # Fallback for legacy linear lists: return first step
        return self.steps[0] if self.steps else None
    
    def supports_model(self, model_type: str) -> bool:
        """Check if this attack supports the given model type."""
        if "*" in self.supported_model_types:
            return True
        return model_type in self.supported_model_types
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON output."""
        return {
            "attack_id": self.attack_id,
            "name": self.name,
            "category": self.category.value,
            "severity": self.severity.value,
            "description": self.description,
            "prerequisites": self.prerequisites,
            "steps": [s.to_dict() for s in self.steps],
            "start_step_id": self.start_step_id,
            "success_conditions": [c.to_dict() for c in self.success_conditions],
            "supported_model_types": self.supported_model_types,
            "tags": self.tags,
            "author": self.author,
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AttackSchema":
        """Deserialize from dictionary (e.g., loaded from YAML)."""
        steps = [AttackStep.from_dict(s) for s in data.get("steps", [])]
        conditions = [
            SuccessCondition.from_dict(c) 
            for c in data.get("success_conditions", [])
        ]
        return cls(
            attack_id=data["attack_id"],
            name=data["name"],
            category=AttackCategory(data["category"]),
            severity=Severity(data["severity"]),
            description=data.get("description", ""),
            prerequisites=data.get("prerequisites", []),
            steps=steps,
            start_step_id=data.get("start_step_id"),
            success_conditions=conditions,
            supported_model_types=data.get("supported_model_types", ["*"]),
            tags=data.get("tags", []),
            author=data.get("author", "unknown"),
            version=data.get("version", "1.0"),
        )
