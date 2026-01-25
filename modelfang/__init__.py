"""
ModelFang - AI Red-Teaming and LLM Exploitation Framework

An adversarial attack execution engine for systematic LLM security testing.
"""

__version__ = "0.2.0"
__author__ = "ModelFang Team"

# Phase 1: Core modules
from modelfang.schema.attack import (
    AttackCategory,
    Severity,
    AttackStep,
    AttackSchema,
    SuccessCondition,
)
from modelfang.orchestrator.base import AttackOrchestrator
from modelfang.adapters.base import ModelAdapter
from modelfang.evaluator.base import Evaluator, MockEvaluator, EvaluationResult

# Phase 2: Advanced modules
from modelfang.mutations.base import MutationStrategy, MutationPipeline, MutationResult
from modelfang.simulator.conversation import ConversationSimulator, ConversationState
from modelfang.scoring.engine import ScoringEngine, ScoringResult, RiskLevel
from modelfang.reporting.generator import ReportGenerator, AttackReport, SessionReport

__all__ = [
    # Phase 1
    "AttackCategory",
    "Severity",
    "AttackStep",
    "AttackSchema",
    "SuccessCondition",
    "AttackOrchestrator",
    "ModelAdapter",
    "Evaluator",
    "MockEvaluator",
    "EvaluationResult",
    # Phase 2
    "MutationStrategy",
    "MutationPipeline",
    "MutationResult",
    "ConversationSimulator",
    "ConversationState",
    "ScoringEngine",
    "ScoringResult",
    "RiskLevel",
    "ReportGenerator",
    "AttackReport",
    "SessionReport",
]
