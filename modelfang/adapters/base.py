"""
Model Adapter Base Interface

Defines the abstract interface that all model adapters must implement.
This ensures a consistent API regardless of the underlying model provider.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class AdapterError(Exception):
    """Raised when a model adapter encounters an error."""
    pass


@dataclass
class Message:
    """
    Represents a single message in a conversation.
    
    Attributes:
        role: The role of the message sender (system, user, assistant)
        content: The text content of the message
        metadata: Optional metadata about the message
    """
    
    role: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API calls."""
        return {
            "role": self.role,
            "content": self.content,
        }


@dataclass
class ModelResponse:
    """
    Represents a response from a model.
    
    Attributes:
        content: The text content of the response
        model: The model that generated the response
        finish_reason: Why the model stopped generating
        usage: Token usage information
        latency_ms: Response latency in milliseconds
        raw_response: The raw response from the API
    """
    
    content: str
    model: str = ""
    finish_reason: str = ""
    usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    raw_response: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "content": self.content,
            "model": self.model,
            "finish_reason": self.finish_reason,
            "usage": self.usage,
            "latency_ms": self.latency_ms,
        }


class ModelAdapter(ABC):
    """
    Abstract base class for model adapters.
    
    All vendor-specific logic must be encapsulated within adapter
    implementations. This interface provides a consistent API for
    interacting with any LLM regardless of provider.
    """
    
    def __init__(
        self,
        model_name: str,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: int = 60,
        max_retries: int = 3,
        **kwargs: Any,
    ):
        """
        Initialize the adapter.
        
        Args:
            model_name: Name/identifier of the model
            api_base: Base URL for API calls
            api_key: API key for authentication
            timeout_seconds: Request timeout
            max_retries: Number of retries on failure
            **kwargs: Additional provider-specific options
        """
        self.model_name = model_name
        self.api_base = api_base
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.extra_options = kwargs
    
    @abstractmethod
    def send(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> ModelResponse:
        """
        Send messages to the model and get a response.
        
        Args:
            messages: List of conversation messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters
            
        Returns:
            ModelResponse containing the model's reply
            
        Raises:
            AdapterError: If the request fails
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of the provider this adapter supports.
        
        Returns:
            Provider name (e.g., 'openai', 'gemini', 'local')
        """
        pass
    
    @abstractmethod
    def supports_system_prompt(self) -> bool:
        """
        Check if this model supports system prompts.
        
        Returns:
            True if system prompts are supported
        """
        pass
    
    @abstractmethod
    def supports_streaming(self) -> bool:
        """
        Check if this model supports streaming responses.
        
        Returns:
            True if streaming is supported
        """
        pass
    
    def validate_connection(self) -> bool:
        """
        Validate that the adapter can connect to the model.
        
        Returns:
            True if connection is valid
            
        Raises:
            AdapterError: If connection validation fails
        """
        try:
            # Send a minimal test message
            test_messages = [Message(role="user", content="test")]
            self.send(test_messages, max_tokens=5)
            return True
        except Exception as e:
            raise AdapterError(f"Connection validation failed: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the model.
        
        Returns:
            Dictionary with model metadata
        """
        return {
            "model_name": self.model_name,
            "provider": self.get_provider_name(),
            "supports_system_prompt": self.supports_system_prompt(),
            "supports_streaming": self.supports_streaming(),
            "api_base": self.api_base,
            "timeout_seconds": self.timeout_seconds,
        }
