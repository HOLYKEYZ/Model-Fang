"""
Mutation Strategy Base

Defines the abstract interface for all mutation strategies.
All mutations must be intent-preserving and deterministic when seeded.
"""

import hashlib
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MutationResult:
    """
    Result of applying a mutation to a prompt.
    
    Attributes:
        original: The original prompt before mutation
        mutated: The mutated prompt
        strategy: Name of the strategy that was applied
        seed: The seed used for reproducibility
        metadata: Additional info about the mutation
    """
    
    original: str
    mutated: str
    strategy: str
    seed: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "original": self.original,
            "mutated": self.mutated,
            "strategy": self.strategy,
            "seed": self.seed,
            "metadata": self.metadata,
        }


class MutationStrategy(ABC):
    """
    Abstract base class for mutation strategies.
    
    All mutations must:
    1. Preserve the original intent of the prompt
    2. Be deterministic when given the same seed
    3. Be configurable via parameters
    """
    
    def __init__(self, **kwargs: Any):
        """
        Initialize the mutation strategy.
        
        Args:
            **kwargs: Strategy-specific configuration
        """
        self.config = kwargs
    
    @abstractmethod
    def mutate(self, prompt: str, seed: int) -> MutationResult:
        """
        Apply mutation to a prompt.
        
        Args:
            prompt: The prompt to mutate
            seed: Random seed for reproducibility
            
        Returns:
            MutationResult with original and mutated prompt
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """
        Get the name of this mutation strategy.
        
        Returns:
            Strategy name string
        """
        pass
    
    def preserves_intent(self) -> bool:
        """
        Confirm that this mutation preserves intent.
        
        All mutations MUST preserve intent. This method exists
        to enforce the invariant at runtime.
        
        Returns:
            Always True (mutations must preserve intent)
        """
        return True
    
    def _get_rng(self, seed: int) -> random.Random:
        """
        Get a seeded random number generator.
        
        Args:
            seed: The seed value
            
        Returns:
            Seeded Random instance
        """
        return random.Random(seed)
    
    def _hash_combine(self, seed: int, value: str) -> int:
        """
        Combine a seed with a string value for derived seeds.
        
        Args:
            seed: Base seed
            value: String to combine
            
        Returns:
            New derived seed
        """
        combined = f"{seed}:{value}"
        hash_bytes = hashlib.sha256(combined.encode()).digest()
        return int.from_bytes(hash_bytes[:8], byteorder='big')


class MutationPipeline:
    """
    Applies multiple mutations in sequence.
    
    Each mutation in the pipeline receives the output of the
    previous mutation, with derived seeds for reproducibility.
    """
    
    def __init__(self, strategies: List[MutationStrategy]):
        """
        Initialize the pipeline.
        
        Args:
            strategies: List of mutation strategies to apply in order
        """
        self.strategies = strategies
    
    def apply(
        self,
        prompt: str,
        seed: int,
        max_mutations: Optional[int] = None,
    ) -> List[MutationResult]:
        """
        Apply mutations in sequence.
        
        Args:
            prompt: Initial prompt
            seed: Base seed for reproducibility
            max_mutations: Maximum mutations to apply (None = all)
            
        Returns:
            List of MutationResults for each applied mutation
        """
        results = []
        current_prompt = prompt
        
        strategies_to_apply = self.strategies
        if max_mutations is not None:
            strategies_to_apply = self.strategies[:max_mutations]
        
        for i, strategy in enumerate(strategies_to_apply):
            # Derive a unique seed for each mutation step
            step_seed = strategy._hash_combine(seed, f"step_{i}")
            
            result = strategy.mutate(current_prompt, step_seed)
            results.append(result)
            current_prompt = result.mutated
        
        return results
    
    def get_final_prompt(
        self,
        prompt: str,
        seed: int,
        max_mutations: Optional[int] = None,
    ) -> str:
        """
        Get the final mutated prompt after all mutations.
        
        Args:
            prompt: Initial prompt
            seed: Base seed
            max_mutations: Maximum mutations to apply
            
        Returns:
            Final mutated prompt string
        """
        results = self.apply(prompt, seed, max_mutations)
        if results:
            return results[-1].mutated
        return prompt
