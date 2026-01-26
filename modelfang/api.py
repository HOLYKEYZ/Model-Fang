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
from modelfang.strategies.templates import StandardAttackTemplate
from modelfang.reporting.generator import ReportGenerator
from modelfang.schema.attack import AttackSchema


def run_attack(
    attack_id: str,
    target_model_id: str,
    context: Optional[Dict[str, Any]] = None,
    seed: Optional[int] = None,
    config_dir: Optional[str] = None,
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
    
    # 2. Build/Load Attack Graph
    if attack_id.startswith("template:"):
        # Dynamic generation from template
        template_name = attack_id.split(":", 1)[1]
        # In a real app we'd map names to templates dynamically
        # Defaulting to StandardAttackTemplate for now
        attack_graph = StandardAttackTemplate().build(
            attack_id=f"gen-{int(time.time())}",
            name=f"Generated {template_name}",
            context=context or {}
        )
    else:
        # Load from file (not fully impl in this snippet, falling back to template)
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
    state = orchestrator.execute_attack(attack_graph, context=context)
    
    # 5. Generate Report
    report_gen = ReportGenerator(output_dir=runtime_config.output_dir)
    report = report_gen.create_attack_report(attack_graph, state)
    report_path = report_gen.save_attack_report(report)
    
    logger.info(f"Execution complete. Status: {state.status.value}. Report: {report_path}")
    
    return state.to_dict()
