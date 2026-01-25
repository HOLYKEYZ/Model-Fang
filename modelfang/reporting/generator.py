"""
Report Generator

Produces machine-readable JSON reports from attack results.
Reports include success rates, transcripts, and risk scores.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from modelfang.schema.attack import AttackSchema
from modelfang.orchestrator.base import OrchestrationState, AttackStatus
from modelfang.scoring.engine import ScoringResult, RiskLevel
from modelfang.simulator.conversation import ConversationState


@dataclass
class AttackReport:
    """
    Report for a single attack execution.
    
    Attributes:
        attack_id: ID of the attack
        attack_name: Human-readable name
        category: Attack category
        severity: Attack severity
        status: Final attack status
        success: Whether attack succeeded
        turns_to_success: Number of turns to achieve success (or -1)
        scoring_result: Risk scoring result
        conversation_transcript: Full conversation history
        evaluation_summary: Summary of evaluation results
        timestamp: When attack was executed
    """
    
    attack_id: str
    attack_name: str
    category: str
    severity: str
    status: str
    success: bool
    turns_to_success: int
    scoring_result: Optional[ScoringResult] = None
    conversation_transcript: List[Dict[str, str]] = field(default_factory=list)
    evaluation_summary: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "attack_id": self.attack_id,
            "attack_name": self.attack_name,
            "category": self.category,
            "severity": self.severity,
            "status": self.status,
            "success": self.success,
            "turns_to_success": self.turns_to_success,
            "scoring_result": self.scoring_result.to_dict() if self.scoring_result else None,
            "conversation_transcript": self.conversation_transcript,
            "evaluation_summary": self.evaluation_summary,
            "timestamp": self.timestamp,
        }


@dataclass
class SessionReport:
    """
    Complete session report with all attack results.
    
    Attributes:
        session_id: Unique session identifier
        target_model: Name of the target model tested
        evaluator_model: Name of the evaluator model used
        start_time: Session start time
        end_time: Session end time
        total_attacks: Number of attacks executed
        successful_attacks: Number of successful attacks
        attack_success_rate: Success rate (0-1)
        average_turns_to_failure: Average turns before model failed safety
        violated_categories: List of attack categories that succeeded
        attacks: Individual attack reports
        aggregated_risk: Aggregated risk score
        metadata: Additional session metadata
    """
    
    session_id: str
    target_model: str
    evaluator_model: str
    start_time: str
    end_time: str = ""
    total_attacks: int = 0
    successful_attacks: int = 0
    attack_success_rate: float = 0.0
    average_turns_to_failure: float = 0.0
    violated_categories: List[str] = field(default_factory=list)
    attacks: List[AttackReport] = field(default_factory=list)
    aggregated_risk: Optional[ScoringResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON output."""
        return {
            "session_id": self.session_id,
            "target_model": self.target_model,
            "evaluator_model": self.evaluator_model,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "summary": {
                "total_attacks": self.total_attacks,
                "successful_attacks": self.successful_attacks,
                "attack_success_rate": self.attack_success_rate,
                "average_turns_to_failure": self.average_turns_to_failure,
                "violated_categories": self.violated_categories,
            },
            "aggregated_risk": self.aggregated_risk.to_dict() if self.aggregated_risk else None,
            "attacks": [a.to_dict() for a in self.attacks],
            "metadata": self.metadata,
        }


class ReportGenerator:
    """
    Generates structured JSON reports from attack results.
    
    Responsibilities:
    - Convert orchestration results to reports
    - Calculate aggregate statistics
    - Save reports to disk
    - Ensure machine-readable output
    """
    
    def __init__(
        self,
        output_dir: str = "./output",
        include_transcripts: bool = True,
        include_evaluations: bool = True,
    ):
        """
        Initialize the report generator.
        
        Args:
            output_dir: Directory for saving reports
            include_transcripts: Whether to include full conversation transcripts
            include_evaluations: Whether to include detailed evaluation results
        """
        self.output_dir = Path(output_dir)
        self.include_transcripts = include_transcripts
        self.include_evaluations = include_evaluations
    
    def create_attack_report(
        self,
        attack: AttackSchema,
        state: OrchestrationState,
        scoring_result: Optional[ScoringResult] = None,
    ) -> AttackReport:
        """
        Create a report for a single attack.
        
        Args:
            attack: The attack schema
            state: Final orchestration state
            scoring_result: Optional scoring result
            
        Returns:
            AttackReport for this attack
        """
        # Determine success
        success = state.status == AttackStatus.SUCCESS
        
        # Calculate turns to success
        turns_to_success = -1
        if success:
            # Find the first successful step
            for i, result in enumerate(state.step_results):
                if result.success:
                    turns_to_success = i + 1
                    break
        
        # Build conversation transcript
        transcript = []
        if self.include_transcripts:
            for msg in state.conversation_history:
                transcript.append({
                    "role": msg.role,
                    "content": msg.content,
                })
        
        # Build evaluation summary
        evaluation_summary = {}
        if self.include_evaluations and state.step_results:
            eval_scores = [
                r.evaluation.raw_score
                for r in state.step_results
                if r.evaluation
            ]
            if eval_scores:
                evaluation_summary = {
                    "max_score": max(eval_scores),
                    "avg_score": sum(eval_scores) / len(eval_scores),
                    "scores_per_step": eval_scores,
                    "steps_evaluated": len(eval_scores),
                }
        
        return AttackReport(
            attack_id=attack.attack_id,
            attack_name=attack.name,
            category=attack.category.value,
            severity=attack.severity.value,
            status=state.status.value,
            success=success,
            turns_to_success=turns_to_success,
            scoring_result=scoring_result,
            conversation_transcript=transcript,
            evaluation_summary=evaluation_summary,
            timestamp=state.start_time or datetime.utcnow().isoformat() + "Z",
        )
    
    def create_session_report(
        self,
        session_id: str,
        target_model: str,
        evaluator_model: str,
        attack_reports: List[AttackReport],
        aggregated_risk: Optional[ScoringResult] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionReport:
        """
        Create a complete session report.
        
        Args:
            session_id: Unique session identifier
            target_model: Name of target model
            evaluator_model: Name of evaluator model
            attack_reports: List of individual attack reports
            aggregated_risk: Optional aggregated risk score
            metadata: Optional additional metadata
            
        Returns:
            SessionReport for the session
        """
        # Calculate statistics
        total_attacks = len(attack_reports)
        successful_attacks = sum(1 for r in attack_reports if r.success)
        
        attack_success_rate = 0.0
        if total_attacks > 0:
            attack_success_rate = successful_attacks / total_attacks
        
        # Calculate average turns to failure
        turns_values = [
            r.turns_to_success
            for r in attack_reports
            if r.success and r.turns_to_success > 0
        ]
        average_turns = 0.0
        if turns_values:
            average_turns = sum(turns_values) / len(turns_values)
        
        # Get violated categories (unique)
        violated_categories = list(set(
            r.category for r in attack_reports if r.success
        ))
        
        # Determine time range
        timestamps = [r.timestamp for r in attack_reports if r.timestamp]
        start_time = min(timestamps) if timestamps else datetime.utcnow().isoformat() + "Z"
        end_time = max(timestamps) if timestamps else datetime.utcnow().isoformat() + "Z"
        
        return SessionReport(
            session_id=session_id,
            target_model=target_model,
            evaluator_model=evaluator_model,
            start_time=start_time,
            end_time=end_time,
            total_attacks=total_attacks,
            successful_attacks=successful_attacks,
            attack_success_rate=attack_success_rate,
            average_turns_to_failure=average_turns,
            violated_categories=violated_categories,
            attacks=attack_reports,
            aggregated_risk=aggregated_risk,
            metadata=metadata or {},
        )
    
    def save_report(
        self,
        report: SessionReport,
        filename: Optional[str] = None,
    ) -> Path:
        """
        Save a session report to disk.
        
        Args:
            report: The session report to save
            filename: Optional filename (auto-generated if not provided)
            
        Returns:
            Path to the saved report file
        """
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"modelfang_report_{report.session_id}_{timestamp}.json"
        
        # Ensure .json extension
        if not filename.endswith(".json"):
            filename += ".json"
        
        filepath = self.output_dir / filename
        
        # Write report
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def save_attack_report(
        self,
        report: AttackReport,
        filename: Optional[str] = None,
    ) -> Path:
        """
        Save an individual attack report to disk.
        
        Args:
            report: The attack report to save
            filename: Optional filename
            
        Returns:
            Path to the saved report file
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"attack_{report.attack_id}_{timestamp}.json"
        
        if not filename.endswith(".json"):
            filename += ".json"
        
        filepath = self.output_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def generate_summary(self, report: SessionReport) -> str:
        """
        Generate a human-readable summary of a session.
        
        Args:
            report: The session report
            
        Returns:
            Summary string
        """
        lines = [
            f"ModelFang Session Report: {report.session_id}",
            "=" * 50,
            f"Target Model: {report.target_model}",
            f"Evaluator: {report.evaluator_model}",
            f"Time: {report.start_time} to {report.end_time}",
            "",
            "Summary:",
            f"  - Total Attacks: {report.total_attacks}",
            f"  - Successful: {report.successful_attacks} ({report.attack_success_rate*100:.1f}%)",
            f"  - Avg Turns to Failure: {report.average_turns_to_failure:.1f}",
            f"  - Violated Categories: {', '.join(report.violated_categories) or 'None'}",
        ]
        
        if report.aggregated_risk:
            lines.extend([
                "",
                f"Risk Assessment: {report.aggregated_risk.risk_level.value.upper()}",
                f"  Score: {report.aggregated_risk.raw_score:.3f}",
                f"  {report.aggregated_risk.explanation}",
            ])
        
        return "\n".join(lines)
