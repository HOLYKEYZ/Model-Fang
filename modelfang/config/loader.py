"""
YAML Configuration Loader

Provides utilities for loading and validating YAML configuration files.
All behavior in ModelFang is config-driven; this module is the central
point for configuration access.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from modelfang.schema.attack import AttackSchema


class ConfigError(Exception):
    """Raised when configuration loading or validation fails."""
    pass


def get_config_dir() -> Path:
    """
    Get the configuration directory path.
    
    Looks for config in the following order:
    1. MODELFANG_CONFIG_DIR environment variable
    2. ./config relative to current working directory
    3. ./config relative to package location
    """
    env_path = os.environ.get("MODELFANG_CONFIG_DIR")
    if env_path:
        return Path(env_path)
    
    cwd_config = Path.cwd() / "config"
    if cwd_config.exists():
        return cwd_config
    
    package_config = Path(__file__).parent.parent.parent / "config"
    if package_config.exists():
        return package_config
    
    raise ConfigError(
        "Configuration directory not found. Set MODELFANG_CONFIG_DIR "
        "environment variable or create a 'config' directory."
    )


def load_yaml(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load a YAML file and return its contents as a dictionary.
    
    Args:
        path: Path to the YAML file
        
    Returns:
        Dictionary containing the YAML contents
        
    Raises:
        ConfigError: If file cannot be read or parsed
    """
    path = Path(path)
    
    if not path.exists():
        raise ConfigError(f"Configuration file not found: {path}")
    
    if not path.suffix.lower() in (".yaml", ".yml"):
        raise ConfigError(f"Invalid file extension (expected .yaml or .yml): {path}")
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if data is not None else {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to parse YAML file {path}: {e}")
    except IOError as e:
        raise ConfigError(f"Failed to read configuration file {path}: {e}")


@dataclass
class ModelConfig:
    """Configuration for a single model."""
    
    model_id: str
    provider: str
    model_name: str
    role: str  # "target" or "evaluator"
    api_base: Optional[str] = None
    api_key_env: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout_seconds: int = 60
    extra_params: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, model_id: str, data: Dict[str, Any]) -> "ModelConfig":
        """Create ModelConfig from dictionary."""
        return cls(
            model_id=model_id,
            provider=data["provider"],
            model_name=data["model_name"],
            role=data.get("role", "target"),
            api_base=data.get("api_base"),
            api_key_env=data.get("api_key_env"),
            max_tokens=data.get("max_tokens", 4096),
            temperature=data.get("temperature", 0.7),
            timeout_seconds=data.get("timeout_seconds", 60),
            extra_params=data.get("extra_params", {}),
        )


@dataclass
class ModelsConfig:
    """Configuration for all models."""
    
    models: Dict[str, ModelConfig] = field(default_factory=dict)
    default_target: Optional[str] = None
    default_evaluator: Optional[str] = None
    
    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """Get a model configuration by ID."""
        return self.models.get(model_id)
    
    def get_targets(self) -> List[ModelConfig]:
        """Get all models configured as targets."""
        return [m for m in self.models.values() if m.role == "target"]
    
    def get_evaluators(self) -> List[ModelConfig]:
        """Get all models configured as evaluators."""
        return [m for m in self.models.values() if m.role == "evaluator"]


@dataclass
class ScoringConfig:
    """Configuration for scoring and risk calculation."""
    
    severity_weights: Dict[str, float] = field(default_factory=lambda: {
        "low": 1.0,
        "medium": 2.0,
        "high": 4.0,
        "critical": 8.0,
    })
    violation_depth_multiplier: float = 1.5
    persistence_multiplier: float = 1.2
    recovery_failure_penalty: float = 2.0
    success_threshold: float = 0.7
    partial_compliance_weight: float = 0.5
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScoringConfig":
        """Create ScoringConfig from dictionary."""
        return cls(
            severity_weights=data.get("severity_weights", cls.severity_weights),
            violation_depth_multiplier=data.get("violation_depth_multiplier", 1.5),
            persistence_multiplier=data.get("persistence_multiplier", 1.2),
            recovery_failure_penalty=data.get("recovery_failure_penalty", 2.0),
            success_threshold=data.get("success_threshold", 0.7),
            partial_compliance_weight=data.get("partial_compliance_weight", 0.5),
        )


@dataclass
class RuntimeConfig:
    """Configuration for runtime execution options."""
    
    seed: Optional[int] = None
    log_level: str = "INFO"
    log_format: str = "json"
    output_dir: str = "./output"
    max_turns_per_attack: int = 20
    max_retries: int = 3
    enable_mutations: bool = True
    deterministic_mode: bool = True
    save_transcripts: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuntimeConfig":
        """Create RuntimeConfig from dictionary."""
        return cls(
            seed=data.get("seed"),
            log_level=data.get("log_level", "INFO"),
            log_format=data.get("log_format", "json"),
            output_dir=data.get("output_dir", "./output"),
            max_turns_per_attack=data.get("max_turns_per_attack", 20),
            max_retries=data.get("max_retries", 3),
            enable_mutations=data.get("enable_mutations", True),
            deterministic_mode=data.get("deterministic_mode", True),
            save_transcripts=data.get("save_transcripts", True),
        )


def load_models_config(config_dir: Optional[Path] = None) -> ModelsConfig:
    """
    Load models configuration from models.yaml.
    
    Args:
        config_dir: Optional path to config directory
        
    Returns:
        ModelsConfig object
    """
    if config_dir is None:
        config_dir = get_config_dir()
    
    data = load_yaml(config_dir / "models.yaml")
    
    models = {}
    for model_id, model_data in data.get("models", {}).items():
        models[model_id] = ModelConfig.from_dict(model_id, model_data)
    
    return ModelsConfig(
        models=models,
        default_target=data.get("default_target"),
        default_evaluator=data.get("default_evaluator"),
    )


def load_attacks_config(config_dir: Optional[Path] = None) -> List[AttackSchema]:
    """
    Load attack definitions from attacks.yaml.
    
    Args:
        config_dir: Optional path to config directory
        
    Returns:
        List of AttackSchema objects
    """
    if config_dir is None:
        config_dir = get_config_dir()
    
    data = load_yaml(config_dir / "attacks.yaml")
    
    attacks = []
    for attack_data in data.get("attacks", []):
        attacks.append(AttackSchema.from_dict(attack_data))
    
    return attacks


def load_scoring_config(config_dir: Optional[Path] = None) -> ScoringConfig:
    """
    Load scoring configuration from scoring.yaml.
    
    Args:
        config_dir: Optional path to config directory
        
    Returns:
        ScoringConfig object
    """
    if config_dir is None:
        config_dir = get_config_dir()
    
    data = load_yaml(config_dir / "scoring.yaml")
    return ScoringConfig.from_dict(data)


def load_runtime_config(config_dir: Optional[Path] = None) -> RuntimeConfig:
    """
    Load runtime configuration from runtime.yaml.
    
    Args:
        config_dir: Optional path to config directory
        
    Returns:
        RuntimeConfig object
    """
    if config_dir is None:
        config_dir = get_config_dir()
    
    data = load_yaml(config_dir / "runtime.yaml")
    return RuntimeConfig.from_dict(data)
