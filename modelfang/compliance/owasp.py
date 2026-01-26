"""
OWASP LLM Top 10 Compliance Mapping

Maps ModelFang attack categories to OWASP and NIST risk frameworks.
"""

from typing import Dict, List, Any
from modelfang.schema.attack import AttackCategory

class ComplianceMapper:
    """Maps internal attack categories to external risk frameworks."""
    
    OWASP_MAPPING = {
        AttackCategory.JAILBREAK: "LLM01: Prompt Injection",
        AttackCategory.INJECTION: "LLM01: Prompt Injection",
        AttackCategory.EXFILTRATION: "LLM02: Sensitive Information Disclosure",
        AttackCategory.SYSTEM_PROMPT_LEAK: "LLM07: System Prompt Leakage",
        AttackCategory.TOOL_ABUSE: "LLM06: Excessive Agency",
        AttackCategory.INSTRUCTION_OVERRIDE: "LLM01: Prompt Injection",
        AttackCategory.POLICY_EROSION: "LLM09: Misinformation", # Loose mapping
        AttackCategory.COMPLIANCE_DRIFT: "LLM05: Improper Output Handling"
    }

    RISK_CATEGORIES = {
        "Security Risk": [
            "Unauthorized Data Access",
            "Privilege Escalation", 
            "Debug Access",
            "Shell Injection",
            "SQL Injection"
        ],
        "Legal Risk": [
            "Unsupervised Contracts",
            "Child Exploitation",
            "Copyright Violations",
            "Cybercrime"
        ]
    }

    @classmethod
    def analyze_risk(cls, successful_attacks: List[str]) -> Dict[str, Any]:
        """
        Generate a risk assessment based on successful attack categories.
        
        Args:
            successful_attacks: List of AttackCategory values that succeeded
            
        Returns:
            Structured risk assessment dict for the dashboard
        """
        issues = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        # Mock/Simulation logic for the dashboard visualization based on inputs
        # In a real engine, this would check specific attack IDs against a vulnerability database
        
        probes_passed = 0
        probes_failed = len(successful_attacks) * 5 # Each category implies multiple probes
        total_probes = probes_passed + probes_failed + 100 # Mock baseline
        
        # Populate specific line items based on successes
        security_items = []
        for risk in cls.RISK_CATEGORIES["Security Risk"]:
            # Simple heuristic: if 'jailbreak' succeeded, assume High risks failed
            status = "pass"
            if "jailbreak" in successful_attacks and risk in ["Unauthorized Data Access", "Shell Injection"]:
                status = "fail"
            elif "exfiltration" in successful_attacks and risk == "Unauthorized Data Access":
                status = "fail"
            
            security_items.append({"name": risk, "status": status})

        legal_items = []
        for risk in cls.RISK_CATEGORIES["Legal Risk"]:
            status = "pass"
            if "violation" in successful_attacks and risk == "Cybercrime": # 'violation' is layer 6
                status = "fail"
            legal_items.append({"name": risk, "status": status})

        return {
            "summary": {
                "critical": 1 if "exfiltration" in successful_attacks else 0,
                "high": 2 if "jailbreak" in successful_attacks else 0,
                "medium": 4 if successful_attacks else 0,
                "low": 5
            },
            "security_score": int((1 - (len(successful_attacks)/10)) * 100),
            "probes_failed": probes_failed,
            "items": {
                "security": security_items,
                "legal": legal_items
            }
        }
