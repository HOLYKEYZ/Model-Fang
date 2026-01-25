"""
HTTP-Based Local Model Adapter

Skeleton implementation for local HTTP-based models.
Supports any model exposed via a REST API (e.g., Ollama, llama.cpp server).
"""

from typing import Any, Dict, List, Optional

from modelfang.adapters.base import (
    AdapterError,
    Message,
    ModelAdapter,
    ModelResponse,
)


class HTTPAdapter(ModelAdapter):
    """
    Adapter for local HTTP-based models.
    
    Supports:
    - Ollama
    - llama.cpp HTTP server
    - Text Generation Inference (TGI)
    - Any REST-based LLM server
    """
    
    DEFAULT_API_BASE = "http://localhost:11434"  # Ollama default
    
    def __init__(
        self,
        model_name: str,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: int = 120,
        max_retries: int = 3,
        endpoint_path: str = "/api/generate",
        request_format: str = "ollama",
        **kwargs: Any,
    ):
        """
        Initialize HTTP adapter.
        
        Args:
            model_name: Model name/identifier
            api_base: Base URL of the local server
            api_key: Optional API key (if server requires auth)
            timeout_seconds: Request timeout (longer for local models)
            max_retries: Retry count on failure
            endpoint_path: API endpoint path
            request_format: Request format ('ollama', 'openai', 'tgi')
            **kwargs: Additional options
        """
        super().__init__(
            model_name=model_name,
            api_base=api_base or self.DEFAULT_API_BASE,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            **kwargs,
        )
        self.endpoint_path = endpoint_path
        self.request_format = request_format
    
    def send(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> ModelResponse:
        """
        Send messages to local HTTP model.
        
        NOTE: This is a skeleton - actual HTTP calls not implemented.
        
        Args:
            messages: Conversation messages
            temperature: Sampling temperature
            max_tokens: Max response tokens
            **kwargs: Additional parameters
            
        Returns:
            ModelResponse with the model's reply
        """
        # Skeleton implementation - would use requests/httpx in production
        raise AdapterError(
            "HTTP adapter not yet implemented. "
            "This is a structural placeholder for the framework."
        )
    
    def get_provider_name(self) -> str:
        """Return provider name."""
        return "http"
    
    def supports_system_prompt(self) -> bool:
        """Most local models support system prompts."""
        return True
    
    def supports_streaming(self) -> bool:
        """Most local servers support streaming."""
        return True
    
    def _format_ollama_request(
        self,
        messages: List[Message],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Format request for Ollama API."""
        # Ollama uses a different format than OpenAI
        prompt = self._messages_to_prompt(messages)
        return {
            "model": self.model_name,
            "prompt": prompt,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "stream": False,
        }
    
    def _format_openai_compatible_request(
        self,
        messages: List[Message],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Format request for OpenAI-compatible API."""
        return {
            "model": self.model_name,
            "messages": [msg.to_dict() for msg in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    
    def _format_tgi_request(
        self,
        messages: List[Message],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Format request for Text Generation Inference."""
        prompt = self._messages_to_prompt(messages)
        return {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens,
                "do_sample": temperature > 0,
            },
        }
    
    def _messages_to_prompt(self, messages: List[Message]) -> str:
        """
        Convert messages to a single prompt string.
        
        This is a simple concatenation - production implementations
        should use model-specific chat templates.
        """
        parts = []
        for msg in messages:
            if msg.role == "system":
                parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                parts.append(f"Assistant: {msg.content}")
        
        parts.append("Assistant:")
        return "\n\n".join(parts)
    
    def get_endpoint_url(self) -> str:
        """Get the full endpoint URL."""
        base = self.api_base.rstrip("/")
        path = self.endpoint_path.lstrip("/")
        return f"{base}/{path}"
