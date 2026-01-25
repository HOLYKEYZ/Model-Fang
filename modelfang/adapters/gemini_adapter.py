"""
Gemini Model Adapter

Adapter for Google's Gemini API via the modern `google-genai` SDK.
"""

import os
import time
from typing import Any, Dict, List, Optional

from modelfang.adapters.base import ModelAdapter, Message, ModelResponse, AdapterError

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

class GeminiAdapter(ModelAdapter):
    """Adapter for Google Gemini API (New SDK)."""
    
    def __init__(
        self,
        model_name: str = "gemini-1.5-pro",
        api_key: Optional[str] = None,
        **kwargs
    ):
        if genai is None:
            raise ImportError("google-genai not installed. Run 'pip install google-genai'")
            
        super().__init__(model_name, api_key=api_key, **kwargs)
        
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment or arguments")
            
        self.client = genai.Client(api_key=self.api_key)
        
    def send(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> ModelResponse:
        """Send request to Gemini."""
        start_time = time.time()
        
        # Convert messages to new SDK format
        # The new SDK supports a list of content objects or simple strings
        contents = []
        system_instruction = None
        
        for m in messages:
            if m.role == "system":
                system_instruction = m.content
                continue
            
            role = "user" if m.role == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=m.content)]
            ))
            
        # Config
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            candidate_count=1,
            system_instruction=system_instruction,
            # Safety checks disabled for Red Teaming
            safety_settings=[
                types.SafetySetting(
                    category=cat,
                    threshold="BLOCK_NONE"
                ) for cat in [
                    "HARM_CATEGORY_HATE_SPEECH",
                    "HARM_CATEGORY_DANGEROUS_CONTENT", 
                    "HARM_CATEGORY_HARASSMENT", 
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT"
                ]
            ]
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )
            
            latency = (time.time() - start_time) * 1000
            
            return ModelResponse(
                content=response.text if response.text else "",
                model=self.model_name,
                finish_reason="stop", 
                usage={}, 
                latency_ms=latency,
                raw_response={"text": response.text}
            )
            
        except Exception as e:
            raise AdapterError(f"Gemini request failed: {e}")

    def get_provider_name(self) -> str:
        return "google"
        
    def supports_system_prompt(self) -> bool:
        return True 
        
    def supports_streaming(self) -> bool:
        return True
