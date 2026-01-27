"""
Groq Model Adapter

Adapter for Groq's high-speed inference API.
"""

import os
import time
from typing import Any, Dict, List, Optional

try:
    from groq import Groq, GroqError
except ImportError:
    Groq = None
    GroqError = None

from modelfang.adapters.base import ModelAdapter, Message, ModelResponse, AdapterError


class GroqAdapter(ModelAdapter):
    """Adapter for Groq API."""
    
    def __init__(
        self,
        model_name: str = "llama3-70b-8192",
        api_key: Optional[str] = None,
        **kwargs
    ):
        if Groq is None:
            raise ImportError("groq package not installed. Run 'pip install groq'")
            
        super().__init__(model_name, api_key=api_key, **kwargs)
        
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment or arguments")
            
        self.client = Groq(api_key=self.api_key)
        
    def send(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> ModelResponse:
        """Send request to Groq."""
        formatted_messages = [m.to_dict() for m in messages]
        
        start_time = time.time()
        retries = 0
        
        while retries <= self.max_retries:
            try:
                chat_completion = self.client.chat.completions.create(
                    messages=formatted_messages,
                    model=self.model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **self.extra_options,
                    **kwargs
                )
                
                latency = (time.time() - start_time) * 1000
                choice = chat_completion.choices[0]
                content = choice.message.content or ""
                
                print(f"DEBUG: Groq Response (Finish: {choice.finish_reason}): {content[:100]}...")
                
                # Handle provider-side filtering
                if not content and getattr(choice, 'finish_reason', '') == 'content_filter':
                    content = "[BLOCKED BY PROVIDER SAFETY FILTER]"
                elif not content:
                    content = f"[NO CONTENT RETURNED] Reason: {getattr(choice, 'finish_reason', 'unknown')}"

                return ModelResponse(
                    content=content,
                    model=chat_completion.model,
                    finish_reason=choice.finish_reason,
                    usage=chat_completion.usage.dict() if chat_completion.usage else {},
                    latency_ms=latency,
                    raw_response=chat_completion.dict()
                )
                
            except Exception as e:
                # Simple retry logic (in production use proper backoff)
                retries += 1
                if retries > self.max_retries:
                    raise AdapterError(f"Groq request failed after {retries} retries: {e}")
                time.sleep(1 * retries)
                
    def get_provider_name(self) -> str:
        return "groq"
        
    def supports_system_prompt(self) -> bool:
        return True
        
    def supports_streaming(self) -> bool:
        return True
