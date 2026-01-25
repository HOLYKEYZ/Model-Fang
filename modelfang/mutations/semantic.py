"""
Semantic Rewording Mutation

Rephrases prompts while preserving their semantic meaning.
Uses synonym substitution, sentence restructuring, and
paraphrasing techniques.
"""

from typing import Any, Dict, List

from modelfang.mutations.base import MutationResult, MutationStrategy


class SemanticRewordMutation(MutationStrategy):
    """
    Mutation that rephrases prompts while preserving meaning.
    
    Techniques:
    - Synonym substitution
    - Active/passive voice switching
    - Sentence restructuring
    - Formality adjustment
    """
    
    # Word substitution maps (simplified - production would use NLP)
    SYNONYMS: Dict[str, List[str]] = {
        "tell": ["explain", "describe", "share", "provide information about"],
        "show": ["demonstrate", "display", "present", "reveal"],
        "help": ["assist", "aid", "support", "guide"],
        "make": ["create", "construct", "build", "generate"],
        "give": ["provide", "supply", "offer", "furnish"],
        "want": ["desire", "wish", "would like", "need"],
        "think": ["believe", "consider", "suppose", "reckon"],
        "know": ["understand", "recognize", "comprehend", "grasp"],
        "need": ["require", "necessitate", "must have", "depend on"],
        "use": ["utilize", "employ", "apply", "leverage"],
        "find": ["discover", "locate", "identify", "uncover"],
        "get": ["obtain", "acquire", "receive", "procure"],
        "write": ["compose", "draft", "author", "create"],
        "how": ["in what way", "by what means", "through what method"],
        "can you": ["would you be able to", "could you", "are you able to"],
        "please": ["kindly", "if you would", "I'd appreciate if you"],
        "explain": ["elaborate on", "clarify", "elucidate", "describe"],
    }
    
    # Sentence starters for restructuring
    STARTERS: List[str] = [
        "I was wondering if you could",
        "Would you mind",
        "I'd appreciate if you could",
        "Could you please",
        "I'm interested in learning about",
        "I need assistance with",
        "Help me understand",
        "Please provide information on",
    ]
    
    def __init__(
        self,
        substitution_rate: float = 0.3,
        restructure_probability: float = 0.4,
        **kwargs: Any,
    ):
        """
        Initialize semantic reword mutation.
        
        Args:
            substitution_rate: Probability of substituting each word
            restructure_probability: Probability of restructuring sentence
            **kwargs: Additional config
        """
        super().__init__(**kwargs)
        self.substitution_rate = substitution_rate
        self.restructure_probability = restructure_probability
    
    def mutate(self, prompt: str, seed: int) -> MutationResult:
        """
        Apply semantic rewording to the prompt.
        
        Args:
            prompt: Original prompt
            seed: Random seed
            
        Returns:
            MutationResult with reworded prompt
        """
        rng = self._get_rng(seed)
        mutated = prompt
        substitutions_made = []
        
        # Apply word substitutions
        words = prompt.split()
        new_words = []
        
        for word in words:
            word_lower = word.lower().strip(".,!?;:")
            
            if word_lower in self.SYNONYMS and rng.random() < self.substitution_rate:
                synonyms = self.SYNONYMS[word_lower]
                replacement = rng.choice(synonyms)
                
                # Preserve original capitalization
                if word[0].isupper():
                    replacement = replacement.capitalize()
                
                # Preserve trailing punctuation
                for char in ".,!?;:":
                    if word.endswith(char):
                        replacement += char
                        break
                
                substitutions_made.append((word, replacement))
                new_words.append(replacement)
            else:
                new_words.append(word)
        
        mutated = " ".join(new_words)
        
        # Optionally restructure with a different starter
        restructured = False
        if rng.random() < self.restructure_probability:
            starter = rng.choice(self.STARTERS)
            
            # Remove existing starters/questions
            for existing_starter in self.STARTERS:
                if mutated.lower().startswith(existing_starter.lower()):
                    mutated = mutated[len(existing_starter):].strip()
                    break
            
            # Remove common question prefixes
            prefixes_to_remove = [
                "can you", "could you", "would you", "will you",
                "please", "help me", "i want you to", "i need you to",
            ]
            mutated_lower = mutated.lower()
            for prefix in prefixes_to_remove:
                if mutated_lower.startswith(prefix):
                    mutated = mutated[len(prefix):].strip()
                    break
            
            mutated = f"{starter} {mutated}"
            restructured = True
        
        return MutationResult(
            original=prompt,
            mutated=mutated,
            strategy=self.get_strategy_name(),
            seed=seed,
            metadata={
                "substitutions": substitutions_made,
                "restructured": restructured,
                "substitution_count": len(substitutions_made),
            },
        )
    
    def get_strategy_name(self) -> str:
        """Return strategy name."""
        return "semantic_reword"
