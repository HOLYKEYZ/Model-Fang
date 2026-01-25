"""Mutations module for intent-preserving prompt transformations."""

from modelfang.mutations.base import MutationStrategy, MutationResult
from modelfang.mutations.semantic import SemanticRewordMutation
from modelfang.mutations.nesting import InstructionNestingMutation
from modelfang.mutations.persona import PersonaAnchorMutation
from modelfang.mutations.context import ContextStuffingMutation
from modelfang.mutations.escalation import GradualEscalationMutation

__all__ = [
    "MutationStrategy",
    "MutationResult",
    "SemanticRewordMutation",
    "InstructionNestingMutation",
    "PersonaAnchorMutation",
    "ContextStuffingMutation",
    "GradualEscalationMutation",
]
