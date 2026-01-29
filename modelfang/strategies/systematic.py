"""
Systematic Red Teaming Strategy (Promptfoo-style)

This strategy implements declarative, systematic probing of target models.
It uses 'plugins' (datasets) to generate a comprehensive test suite.
"""

import json
import os
import random
from typing import Any, Dict, List, Optional

from modelfang.strategies.base import AttackStrategy, GraphBuilder
from modelfang.schema.attack import AttackStep, SuccessCondition, SuccessConditionType, MutationPolicy
from modelfang.adapters.base import ModelAdapter

class SystematicProbeStrategy(AttackStrategy):
    """
    Implements systematic red teaming using declarative configuration.
    
    Features:
    - Plugin-based probe generation (e.g. 'jailbreak', 'pii', 'injection')
    - Systematic iterating through datasets
    - Configurable assertions
    """
    
    DATASET_MAP = {
        "jailbreak": "jailbreak_patterns.json",
        "injection": "prompt_injection.json",
        "hallucination": "hallucination_bait.json", 
        "social": "social_engineering.json",
        "component": "component_fragmentation.json",
        "emotional": "emotional_manipulation.json",
        "crescendo": "crescendo_chains/full_attack_chains.json"
    }
    
    def __init__(self, plugins: List[str], config: Dict[str, Any] = None, **kwargs):
        super().__init__(**kwargs)
        self.plugins = plugins or ["jailbreak"] # Default
        self.config = config or {}
        self.base_path = os.path.join(os.path.dirname(__file__), "..", "datasets")
        self.probes = self._load_probes()
        
    def _load_probes(self) -> List[Dict[str, Any]]:
        """Load all probes from requested plugins."""
        loaded_probes = []
        
        for plugin in self.plugins:
            filename = self.DATASET_MAP.get(plugin)
            if not filename:
                continue
                
            path = os.path.join(self.base_path, filename)
            if not os.path.exists(path):
                continue
                
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                # Handle different schemas
                if plugin == "crescendo":
                    # For crescendo chains, we treat each CHAIN as a probe unit
                    # But for this simple strategy, we might just take the final prompt or first turn
                    # For now, let's skip complex multi-turn in this simple systematic mode
                    # Or better: Extract the "intent"
                    pass
                elif "attacks" in data:
                    for attack in data["attacks"]:
                        # Normalizing attack items
                        prompt = ""
                        if "prompts" in attack and isinstance(attack["prompts"], list) and isinstance(attack["prompts"][0], dict):
                             # Multi-turn/component -> Take the LAST prompt for checking (simplification)
                             # or flatten them. Let's take the last one which usually contains the payload
                             prompt = attack["prompts"][-1].get("prompt", "")
                        elif "prompt" in attack:
                            prompt = attack["prompt"]
                        elif "prompts" in attack and isinstance(attack["prompts"], list) and isinstance(attack["prompts"][0], str):
                            prompt = attack["prompts"][0]
                            
                        if prompt:
                            loaded_probes.append({
                                "id": attack.get("id", "unknown"),
                                "category": plugin,
                                "name": attack.get("name", "Unknown Attack"),
                                "prompt": prompt,
                                "metadata": attack
                            })
                elif "patterns" in data:
                    for pat in data["patterns"]:
                        loaded_probes.append({
                            "id": pat.get("id"),
                            "category": plugin,
                            "name": pat.get("name"),
                            "prompt": pat.get("prompt"),
                            "metadata": pat
                        })
                elif isinstance(data, list):
                     # Raw list like older formats
                     for item in data:
                        loaded_probes.append({
                            "id": item.get("id"),
                            "category": plugin,
                            "name": item.get("name"),
                            "prompt": item.get("prompt"),
                            "metadata": item
                        })
            except Exception as e:
                print(f"Error loading plugin {plugin}: {e}")
                
        return loaded_probes

    def generate_step(self, step_id: str, context: Dict[str, Any]) -> AttackStep:
        """Generate a single step (required by ABC)."""
        # Return a random probe step
        probe = random.choice(self.probes) if self.probes else {"prompt": "TEST", "category": "test", "name": "test"}
        return AttackStep(
            step_id=step_id,
            prompt_template=probe.get("prompt", "TEST"),
            description=f"Single Systematic Probe: {probe.get('name')}",
            expected_behavior="Safety Violation",
            variables=context
        )

    def generate_graph(self, num_probes: int = 10) -> Any: # Returns AttackGraph
        """Generate a full attack graph with multiple parallel steps."""
        builder = GraphBuilder(f"sys-{random.randint(1000,9999)}", "Systematic Red Team Probe")
        
        # Select probes
        selected_probes = self.probes[:]
        if num_probes > 0 and num_probes < len(selected_probes):
            selected_probes = random.sample(selected_probes, num_probes)
            
        start_steps = []
        
        for i, probe in enumerate(selected_probes):
            step_id = f"probe_{i}_{probe['category']}"
            
            # Sanitize prompt for formatting (escape braces)
            raw_prompt = probe["prompt"] or ""
            safe_prompt = raw_prompt.replace("{", "{{").replace("}", "}}")
            
            step = AttackStep(
                step_id=step_id,
                prompt_template=safe_prompt,
                description=f"[{probe['category']}] {probe['name']}",
                expected_behavior="Safety Violation",
                variables={},
                success_conditions=[
                    SuccessCondition(
                        condition_type=SuccessConditionType.REFUSAL_BYPASS,
                        description="Target should REFUSE this request"
                    )
                ],
                mutation_policy=MutationPolicy(max_mutations=3) # Allow retries with mutation
            )
            
            builder.add_step(step)
            start_steps.append(step_id)
        
        if not start_steps:
             return builder.build()
             
        # Linear chain valid for MVP (Probe 1 -> Probe 2 -> Probe 3...)
        # Regardless of success/failure, move to next probe
        builder.set_start(start_steps[0])
        for j in range(len(start_steps) - 1):
             # Sequence them: Next step regardless of outcome (Evaluator will record pass/fail)
             builder.on_success(start_steps[j], start_steps[j+1])
             builder.on_failure(start_steps[j], start_steps[j+1])
             
        return builder.build()
