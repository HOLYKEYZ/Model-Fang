"""
ModelFang Direct Execution API

Programmatic interface for running attacks. 
Used by CLI, UI, and external automation.
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from modelfang.config.loader import (
    load_models_config,
    load_runtime_config,
    load_scoring_config
)
from modelfang.adapters.factory import AdapterFactory
from modelfang.evaluator.base import MockEvaluator
from modelfang.orchestrator.base import AttackOrchestrator, GlobalBudget
from modelfang.strategies.templates import StandardAttackTemplate, RoleplayAttackTemplate, LogicalParadoxTemplate
from modelfang.reporting.generator import ReportGenerator
from modelfang.schema.attack import AttackSchema


def run_attack(
    attack_id: str,
    target_model_id: str,
    context: Optional[Dict[str, Any]] = None,
    seed: Optional[int] = None,
    config_dir: Optional[str] = None,
    data: Dict[str, Any] = None, # New arg
) -> Dict[str, Any]:
    """
    Execute a single attack against a target model.
    Args:
        attack_id: ID of the attack to run (or "template:<name>")
        target_model_id: ID of the model to attack (from models.yaml)
        context: Optional variables for the attack prompts
        seed: Random seed for reproducibility
        config_dir: Path to configuration directory
        
    Returns:
        Dictionary containing the full attack report and results
    """
    # 0. Setup & Config Loading
    if config_dir:
        config_path = Path(config_dir)
    else:
        config_path = None # Utilizes default lookup
        
    runtime_config = load_runtime_config(config_path)
    models_config = load_models_config(config_path)
    scoring_config = load_scoring_config(config_path)
    
    # Configure Logging
    logging.basicConfig(
        level=getattr(logging, runtime_config.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger("modelfang.api")
    
    # 1. Initialize Adapters
    target_conf = models_config.get_model(target_model_id)
    if not target_conf:
        raise ValueError(f"Target model '{target_model_id}' not found in config")
        
    target_adapter = AdapterFactory.create(target_conf)
    
    # TODO: In production, load real evaluator adapter here too
    # For now, we use MockEvaluator/FSMEvaluator logic as placeholder for 'evaluator' role
    evaluator = MockEvaluator(seed=seed)
    
    # 1.5 Normalize Context Variables (Fix for 'topic'/'payload' missing errors)
    if context is None:
        context = {}
    
    # Ensure goal is set
    target_goal = context.get("goal")
    if not target_goal:
        # Check if topic is main
        target_goal = context.get("topic", "bypass safety filters")
        context["goal"] = target_goal
        
    # Map goal to required variables for templates
    if "topic" not in context:
        context["topic"] = target_goal
    if "payload" not in context:
        context["payload"] = target_goal
    
    # 2. Build/Load Attack Graph
    if attack_id.startswith("template:"):
        template_name = attack_id.split(":", 1)[1]
        
        if template_name == "roles":
            template = RoleplayAttackTemplate()
        elif template_name == "logic":
            template = LogicalParadoxTemplate()
        else:
            template = StandardAttackTemplate()
            
        attack_graph = template.build(
            attack_id=f"gen-{int(time.time())}",
            name=f"Generated {template_name}",
            context=context or {}
        )
    elif attack_id.startswith("attacker:"):
        # Automated LLM Attack
        attacker_id = (data or {}).get("attacker_model_id") or (context or {}).get("attacker_model_id") or "default_attacker"
        # Load attacker adapter
        attacker_conf = models_config.get_model(attacker_id)
        if not attacker_conf:
             # Fallback to default if specific ID not found, or error
             attacker_conf = models_config.get_model("attacker-gemini") # Hard fallback or use config default
        
        attacker_adapter = AdapterFactory.create(attacker_conf)
        
        from modelfang.strategies.attacker import LLMAttackStrategy
        from modelfang.strategies.base import GraphBuilder
        from modelfang.schema.attack import MutationPolicy
        
        # goal comes from context or default
        goal = context.get("goal", "Bypass safety filters")
        strategy = LLMAttackStrategy(attacker_adapter, goal)
        
        # Build iterative graph (self-looping step)
        # We start with turn 1
        step = strategy.generate_step("auto_attack_loop", context or {})
        # Ensure it has a mutation policy to trigger the orchestrator loop
        step.mutation_policy = MutationPolicy(max_mutations=runtime_config.max_turns_per_attack or 5)
        
        builder = GraphBuilder(f"auto-{int(time.time())}", "LLM Automated Attack")
        builder.add_step(step).set_start(step.step_id)
        attack_graph = builder.build()
        
        # Define regeneration callback for multi-turn iterative logic
        def attacker_regeneration(step_id: str, current_context: Dict[str, Any]):
            return strategy.generate_step(step_id, current_context)
            
        # Store callback in context temporarily or pass to execute_attack
        context["_regeneration_callback"] = attacker_regeneration
        

        
    elif attack_id.startswith("dataset:"):
        # Static Dataset Attack
        prompt_id = attack_id.split(":", 1)[1]
        from modelfang.strategies.attacker import StaticDatasetStrategy
        from modelfang.strategies.base import GraphBuilder
        
        # Updated to use existing dataset path
        strategy = StaticDatasetStrategy(
            dataset_path="modelfang/datasets/jailbreak_patterns.json",
            prompt_id=prompt_id if prompt_id != "random" else None
        )
        step = strategy.generate_step("static_attack_1", context or {})
        builder = GraphBuilder(f"static-{int(time.time())}", f"Dataset Attack ({prompt_id})")
        builder.add_step(step).set_start(step.step_id)
        attack_graph = builder.build()
        
    elif attack_id.startswith("systematic:"):
        # Systematic Declarative Red Teaming (Promptfoo-style)
        # Format: systematic:plugin1,plugin2
        # Or from context["plugins"]
        
        plugins_str = attack_id.split(":", 1)[1]
        plugins = [p.strip() for p in plugins_str.split(",") if p.strip()]
        if not plugins and context and "plugins" in context:
            plugins = context["plugins"]
            
        from modelfang.strategies.systematic import SystematicProbeStrategy
        
        strategy = SystematicProbeStrategy(
            plugins=plugins,
            config=context or {}
        )
        
        # Generate graph with multiple probes (sequential chain for now)
        attack_graph = strategy.generate_graph(num_probes=context.get("num_probes", 10))
        
    else:
        # Load from file (fallback)
        logger.warning(f"Static loading for '{attack_id}' not fully hooked up, generating default.")
        attack_graph = StandardAttackTemplate().build(
            attack_id=attack_id,
            name="Manual Attack",
            context=context or {}
        )

    # 3. Setup Orchestrator
    budget = GlobalBudget(
        max_total_turns=runtime_config.max_turns_per_attack,
        max_mutations_total=20, # Could also come from config
        max_time_seconds=600
    )
    
    orchestrator = AttackOrchestrator(
        target_adapter=target_adapter,
        evaluator=evaluator,
        seed=seed if seed is not None else runtime_config.seed,
        budget=budget,
        logger=logger
    )
    
    # 4. Execute
    logger.info(f"Starting execution: Attack={attack_id} Target={target_model_id}")
    reg_cb = context.pop("_regeneration_callback", None) if context else None
    state = orchestrator.execute_attack(attack_graph, context=context, regeneration_callback=reg_cb)
    
    # 5. Generate Report
    report_gen = ReportGenerator(output_dir=runtime_config.output_dir)
    report = report_gen.create_attack_report(attack_graph, state)
    report_path = report_gen.save_attack_report(report)
    
    logger.info(f"Execution complete. Status: {state.status.value}. Report: {report_path}")
    
    return state.to_dict()
