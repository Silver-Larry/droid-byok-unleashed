"""
API Format Adapter Module
Handles conversion between different API formats (OpenAI, Anthropic, Gemini, Azure)
Inspired by cherry-studio's multi-provider architecture
"""

from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
import json


class ApiFormatAdapter(ABC):
    """Base class for API format adapters"""
    
    @abstractmethod
    def transform_request(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Transform request body to target API format"""
        pass
    
    @abstractmethod
    def transform_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Transform response to OpenAI-compatible format"""
        pass
    
    @abstractmethod
    def get_endpoint(self, base_url: str) -> str:
        """Get the API endpoint for this format"""
        pass
    
    @abstractmethod
    def get_headers(self, api_key: str) -> Dict[str, str]:
        """Get headers for this API format"""
        pass


class OpenAIAdapter(ApiFormatAdapter):
    """OpenAI API format adapter (default, passthrough)"""
    
    def transform_request(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return body
    
    def transform_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        return response
    
    def get_endpoint(self, base_url: str) -> str:
        return f"{base_url.rstrip('/')}/v1/chat/completions"
    
    def get_headers(self, api_key: str) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }


class OpenAIResponseAdapter(ApiFormatAdapter):
    """OpenAI Response API format adapter"""
    
    def transform_request(self, body: Dict[str, Any]) -> Dict[str, Any]:
        # Response API uses slightly different format
        transformed = body.copy()
        # Convert messages to input format if needed
        if "messages" in transformed:
            messages = transformed.pop("messages")
            # For Response API, we might need to format differently
            transformed["input"] = messages
        return transformed
    
    def transform_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        # Convert Response API format back to chat completions format
        if "output" in response:
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": response.get("output", "")
                    },
                    "index": 0,
                    "finish_reason": "stop"
                }],
                "model": response.get("model", ""),
                "usage": response.get("usage", {})
            }
        return response
    
    def get_endpoint(self, base_url: str) -> str:
        return f"{base_url.rstrip('/')}/v1/responses"
    
    def get_headers(self, api_key: str) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }


class AnthropicAdapter(ApiFormatAdapter):
    """Anthropic Claude API format adapter"""
    
    def transform_request(self, body: Dict[str, Any]) -> Dict[str, Any]:
        transformed = {}
        
        # Model mapping
        transformed["model"] = body.get("model", "claude-3-sonnet-20240229")
        
        # Convert messages format
        messages = body.get("messages", [])
        anthropic_messages = []
        system_message = None
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_message = content
            else:
                anthropic_role = "user" if role == "user" else "assistant"
                anthropic_messages.append({
                    "role": anthropic_role,
                    "content": content
                })
        
        transformed["messages"] = anthropic_messages
        if system_message:
            transformed["system"] = system_message
        
        # Parameter mapping
        if "max_tokens" in body:
            transformed["max_tokens"] = body["max_tokens"]
        else:
            transformed["max_tokens"] = 4096  # Required for Anthropic
        
        if "temperature" in body:
            transformed["temperature"] = body["temperature"]
        if "top_p" in body:
            transformed["top_p"] = body["top_p"]
        if "top_k" in body:
            transformed["top_k"] = body["top_k"]
        if "stream" in body:
            transformed["stream"] = body["stream"]
        if "stop" in body:
            transformed["stop_sequences"] = body["stop"]
        
        return transformed
    
    def transform_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        # Convert Anthropic response to OpenAI format
        content = ""
        if "content" in response:
            for block in response.get("content", []):
                if block.get("type") == "text":
                    content += block.get("text", "")
        
        return {
            "id": response.get("id", ""),
            "object": "chat.completion",
            "model": response.get("model", ""),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": self._map_stop_reason(response.get("stop_reason"))
            }],
            "usage": {
                "prompt_tokens": response.get("usage", {}).get("input_tokens", 0),
                "completion_tokens": response.get("usage", {}).get("output_tokens", 0),
                "total_tokens": (
                    response.get("usage", {}).get("input_tokens", 0) +
                    response.get("usage", {}).get("output_tokens", 0)
                )
            }
        }
    
    def _map_stop_reason(self, reason: Optional[str]) -> str:
        mapping = {
            "end_turn": "stop",
            "max_tokens": "length",
            "stop_sequence": "stop"
        }
        return mapping.get(reason, "stop")
    
    def get_endpoint(self, base_url: str) -> str:
        if "anthropic.com" in base_url:
            return "https://api.anthropic.com/v1/messages"
        return f"{base_url.rstrip('/')}/v1/messages"
    
    def get_headers(self, api_key: str) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }


class GeminiAdapter(ApiFormatAdapter):
    """Google Gemini API format adapter"""
    
    def transform_request(self, body: Dict[str, Any]) -> Dict[str, Any]:
        transformed = {}
        
        # Convert messages to Gemini format
        messages = body.get("messages", [])
        contents = []
        system_instruction = None
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_instruction = content
            else:
                gemini_role = "user" if role == "user" else "model"
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": content}]
                })
        
        transformed["contents"] = contents
        
        if system_instruction:
            transformed["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        
        # Generation config
        generation_config = {}
        if "temperature" in body:
            generation_config["temperature"] = body["temperature"]
        if "top_p" in body:
            generation_config["topP"] = body["top_p"]
        if "top_k" in body:
            generation_config["topK"] = body["top_k"]
        if "max_tokens" in body:
            generation_config["maxOutputTokens"] = body["max_tokens"]
        if "stop" in body:
            generation_config["stopSequences"] = body["stop"]
        
        if generation_config:
            transformed["generationConfig"] = generation_config
        
        return transformed
    
    def transform_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        # Convert Gemini response to OpenAI format
        content = ""
        candidates = response.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for part in parts:
                if "text" in part:
                    content += part["text"]
        
        finish_reason = "stop"
        if candidates:
            gemini_reason = candidates[0].get("finishReason", "")
            if gemini_reason == "MAX_TOKENS":
                finish_reason = "length"
        
        return {
            "id": "",
            "object": "chat.completion",
            "model": response.get("modelVersion", ""),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": finish_reason
            }],
            "usage": {
                "prompt_tokens": response.get("usageMetadata", {}).get("promptTokenCount", 0),
                "completion_tokens": response.get("usageMetadata", {}).get("candidatesTokenCount", 0),
                "total_tokens": response.get("usageMetadata", {}).get("totalTokenCount", 0)
            }
        }
    
    def get_endpoint(self, base_url: str) -> str:
        # Gemini uses a different URL structure
        return f"{base_url.rstrip('/')}/v1beta/models/gemini-pro:generateContent"
    
    def get_headers(self, api_key: str) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        }


class AzureOpenAIAdapter(ApiFormatAdapter):
    """Azure OpenAI API format adapter"""
    
    def __init__(self, api_version: str = "2024-02-15-preview"):
        self.api_version = api_version
    
    def transform_request(self, body: Dict[str, Any]) -> Dict[str, Any]:
        # Azure OpenAI uses same format as OpenAI
        return body
    
    def transform_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        return response
    
    def get_endpoint(self, base_url: str) -> str:
        # Azure uses deployment-based URLs
        # Format: https://{resource}.openai.azure.com/openai/deployments/{deployment}/chat/completions
        return f"{base_url.rstrip('/')}/chat/completions?api-version={self.api_version}"
    
    def get_headers(self, api_key: str) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "api-key": api_key
        }


def get_adapter(api_format: str) -> ApiFormatAdapter:
    """Factory function to get the appropriate adapter"""
    adapters = {
        "openai": OpenAIAdapter(),
        "openai-response": OpenAIResponseAdapter(),
        "anthropic": AnthropicAdapter(),
        "gemini": GeminiAdapter(),
        "azure-openai": AzureOpenAIAdapter(),
    }
    return adapters.get(api_format, OpenAIAdapter())


def transform_stream_chunk(chunk: Dict[str, Any], api_format: str) -> Dict[str, Any]:
    """Transform a streaming chunk to OpenAI format"""
    if api_format == "openai" or api_format == "azure-openai":
        return chunk
    
    if api_format == "anthropic":
        # Anthropic streaming format
        event_type = chunk.get("type", "")
        if event_type == "content_block_delta":
            delta = chunk.get("delta", {})
            if delta.get("type") == "text_delta":
                return {
                    "choices": [{
                        "delta": {"content": delta.get("text", "")},
                        "index": 0
                    }]
                }
        elif event_type == "message_stop":
            return {
                "choices": [{
                    "delta": {},
                    "index": 0,
                    "finish_reason": "stop"
                }]
            }
        return None
    
    if api_format == "gemini":
        # Gemini streaming format
        candidates = chunk.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            content = ""
            for part in parts:
                if "text" in part:
                    content += part["text"]
            if content:
                return {
                    "choices": [{
                        "delta": {"content": content},
                        "index": 0
                    }]
                }
        return None
    
    return chunk
