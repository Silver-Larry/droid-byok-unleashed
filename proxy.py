"""
Droid BYOK Proxy - A middleware proxy for intercepting and processing
requests/responses between Droid CLI and upstream inference providers.

Features:
- Request enhancement with inference parameters
- Reasoning model parameter injection (DeepSeek, OpenAI, Anthropic, etc.)
- Stream filtering to remove <think>...</think> blocks
- Colored console output for thinking process visualization
- Profile-based configuration with model pattern matching
- Configurable proxy port and API key authentication
"""

import os
import json
import re
import queue
import threading
from typing import List
from functools import wraps
from flask import Flask, request, Response, stream_with_context
from flask_cors import CORS
import requests

from reasoning_config import ReasoningConfig, ReasoningType, ReasoningEffort, get_reasoning_types_info
from reasoning_builder import build_reasoning_params, ReasoningParamsBuilder
from api_format_adapter import get_adapter, transform_stream_chunk
from config_manager import CONFIG_MANAGER, REASONING_TYPES, REASONING_EFFORTS, API_FORMAT_TYPES

app = Flask(__name__)
CORS(app)

# Get proxy settings from unified config manager
PROXY_PORT = CONFIG_MANAGER.proxy.port

# Load defaults from current default profile
_default_profile = CONFIG_MANAGER.get_default_profile()
UPSTREAM_API_KEY = _default_profile.upstream.api_key if _default_profile else ""
UPSTREAM_BASE_URL = _default_profile.upstream.base_url if _default_profile else "https://api.deepseek.com"

# LLM Parameter Configuration
# Defines supported parameters with their types and valid ranges
LLM_PARAMS_CONFIG = {
    "temperature": {"type": float, "range": (0, 2)},
    "top_p": {"type": float, "range": (0, 1)},
    "top_k": {"type": int, "range": (1, 100)},
    "max_tokens": {"type": int, "range": (1, 1000000)},
    "presence_penalty": {"type": float, "range": (-2, 2)},
    "frequency_penalty": {"type": float, "range": (-2, 2)},
    "seed": {"type": int, "range": (0, 2**31 - 1)},
}

# Parameters that should be passed through without validation
PASSTHROUGH_PARAMS = {"stop", "logit_bias", "response_format", "tools", "tool_choice", "user"}

# ANSI color codes for console output
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
DIM = "\033[2m"


def _is_undefined_value(value) -> bool:
    # Cherry Studio (and some OpenAI-compatible clients) may send literal "[undefined]" strings.
    return value is None or value in ("[undefined]", "undefined")


def _prune_undefined(obj):
    """Recursively remove keys/items whose value is None or a literal "[undefined]" string."""
    if isinstance(obj, dict):
        keys_to_delete = []
        for k, v in obj.items():
            if _is_undefined_value(v):
                keys_to_delete.append(k)
                continue
            obj[k] = _prune_undefined(v)
        for k in keys_to_delete:
            del obj[k]
        return obj
    if isinstance(obj, list):
        cleaned = []
        for item in obj:
            if _is_undefined_value(item):
                continue
            cleaned.append(_prune_undefined(item))
        return cleaned
    return obj


# ===================== Thinking SSE Broadcast =====================

_THINKING_SUBSCRIBERS: List[queue.Queue] = []
_THINKING_LOCK = threading.Lock()


def _broadcast_thinking(payload: dict) -> None:
    data = json.dumps(payload, ensure_ascii=False)
    with _THINKING_LOCK:
        for q in list(_THINKING_SUBSCRIBERS):
            try:
                q.put_nowait(data)
            except Exception:
                pass


def require_api_key(f):
    """
    API Key 验证装饰器
    如果设置了 PROXY_API_KEY，则验证请求中的 Authorization header
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # 如果未设置 API Key，跳过验证
        if not CONFIG_MANAGER.proxy.api_key:
            return f(*args, **kwargs)
        
        auth_header = request.headers.get("Authorization", "")
        provided_key = auth_header.replace("Bearer ", "")
        
        if provided_key != CONFIG_MANAGER.proxy.api_key:
            print(f"{RED}[AUTH]{RESET} Invalid API key from {request.remote_addr}")
            return {"error": "Invalid or missing API key"}, 401
        
        return f(*args, **kwargs)
    return decorated


class ThinkingPrinter:
    """Manages thinking content printing with start/end markers."""
    _is_printing = False
    
    @classmethod
    def print(cls, content):
        """Print thinking content, with markers only at start and end."""
        if not cls._is_printing:
            cls._is_printing = True
            print(f"\n{CYAN}[THINKING START]{RESET}")
        print(f"{DIM}{content}{RESET}", end="", flush=True)
    
    @classmethod
    def end(cls):
        """Mark end of thinking block."""
        if cls._is_printing:
            print(f"\n{CYAN}[THINKING END]{RESET}\n")
            cls._is_printing = False


def print_thinking(content):
    """Print thinking content to console with colored output."""
    ThinkingPrinter.print(content)
    _broadcast_thinking({"type": "thinking", "content": content})


def get_default_params():
    """
    Load default LLM parameters from environment variables.
    Environment variable format: DEFAULT_{PARAM_NAME} (uppercase)
    Example: DEFAULT_TEMPERATURE=0.7
    """
    defaults = {}
    for param, config in LLM_PARAMS_CONFIG.items():
        env_key = f"DEFAULT_{param.upper()}"
        env_val = os.environ.get(env_key)
        if env_val is not None:
            try:
                defaults[param] = config["type"](env_val)
            except (ValueError, TypeError) as e:
                print(f"{YELLOW}[WARNING]{RESET} Invalid value for {env_key}: {env_val} - {e}")
    return defaults


def validate_param(name, value, config):
    """
    Validate parameter value against its configuration.
    Returns (is_valid, warning_message, coerced_value).
    """
    if value is None:
        return True, None, None
    
    param_type = config.get("type")
    if param_type and not isinstance(value, param_type):
        try:
            value = param_type(value)
        except (ValueError, TypeError):
            return False, f"Parameter {name} should be of type {param_type.__name__}", None
    
    if "range" in config:
        min_val, max_val = config["range"]
        if not (min_val <= value <= max_val):
            return False, f"Parameter {name}={value} out of range [{min_val}, {max_val}]", None
    
    return True, None, value


def merge_params(body, defaults):
    """
    Merge request parameters with defaults.
    Request parameters take precedence over defaults.
    """
    for param, value in defaults.items():
        if param not in body:
            body[param] = value
    return body


def sanitize_params(body):
    """
    Sanitize and validate LLM parameters in the request body.
    - Validates parameters against their configurations
    - Removes None values
    - Logs warnings for invalid parameters but doesn't block the request
    """
    params_to_remove = []
    
    for param, config in LLM_PARAMS_CONFIG.items():
        if param in body:
            value = body[param]
            if _is_undefined_value(value):
                params_to_remove.append(param)
                continue
            
            is_valid, warning, coerced_value = validate_param(param, value, config)
            if is_valid and coerced_value is not None:
                body[param] = coerced_value
            if not is_valid:
                print(f"{YELLOW}[WARNING]{RESET} {warning}")
                params_to_remove.append(param)
    
    for param in params_to_remove:
        del body[param]

    # Remove passthrough params when client sends undefined placeholders
    for param in list(PASSTHROUGH_PARAMS):
        if param in body and _is_undefined_value(body.get(param)):
            del body[param]
    
    return body


def inject_inference_params(body, effective_config=None):
    """
    Inject and process inference parameters.
    
    This function:
    1. Loads default parameters from environment variables
    2. Merges defaults with request parameters (request takes precedence)
    3. Validates and sanitizes all parameters
    4. Injects reasoning parameters based on effective config from profile
    
    Supported parameters:
    - temperature: Controls randomness (0-2)
    - top_p: Nucleus sampling threshold (0-1)
    - top_k: Top-k sampling (1-100)
    - max_tokens: Maximum output tokens
    - presence_penalty: Penalize new tokens based on presence (-2 to 2)
    - frequency_penalty: Penalize new tokens based on frequency (-2 to 2)
    - seed: Random seed for reproducibility
    - stop: Stop sequences (list of strings)
    
    Reasoning parameters (when enabled):
    - DeepSeek: thinking.type
    - OpenAI: reasoning_effort
    - Anthropic: thinking.budget_tokens
    - Gemini: thinkingConfig
    - Qwen: enable_thinking, thinking_budget
    - OpenRouter: reasoning.enabled, reasoning.effort
    """
    defaults = get_default_params()
    body = merge_params(body, defaults)
    body = sanitize_params(body)
    
    # Merge LLM params from profile
    if effective_config:
        llm_params = effective_config.get("llm_params", {})
        for param, value in llm_params.items():
            if param not in body and value is not None:
                body[param] = value
    
    # Use effective config for reasoning parameters
    if effective_config:
        reasoning_enabled = effective_config.get("reasoning_enabled", False)
        reasoning_type_str = effective_config.get("reasoning_type", "deepseek")
        reasoning_effort_str = effective_config.get("reasoning_effort", "auto")
        budget_tokens = effective_config.get("reasoning_budget_tokens")
        custom_params = effective_config.get("reasoning_custom_params", {})
        
        if reasoning_enabled:
            # Build reasoning config from effective config
            try:
                reasoning_type = ReasoningType(reasoning_type_str)
            except ValueError:
                reasoning_type = ReasoningType.DEEPSEEK
            
            try:
                effort = ReasoningEffort(reasoning_effort_str)
            except ValueError:
                effort = ReasoningEffort.AUTO
            
            temp_config = ReasoningConfig(
                enabled=True,
                reasoning_type=reasoning_type,
                effort=effort,
                budget_tokens=budget_tokens,
                custom_params=custom_params or {},
                filter_thinking_tags=effective_config.get("filter_thinking_tags", True),
            )
            reasoning_params = build_reasoning_params(temp_config)
            if reasoning_params:
                body.update(reasoning_params)
                profile_name = effective_config.get("profile_name", "default")
                print(f"{YELLOW}[REASONING]{RESET} [{profile_name}] Injected: {json.dumps(reasoning_params)}")
    
    # Inject thinking parameter for Zhipu GLM models (official API format)
    # Format: thinking: { type: "enabled" | "disabled" }
    # Supported models: GLM-4.6, GLM-4.6V, GLM-4.5, GLM-4.5V
    model = body.get("model", "")
    zhipu_thinking_models = ["glm-4.6", "glm-4.5", "glm-4.6v", "glm-4.5v"]
    if any(m in model.lower() for m in zhipu_thinking_models):
        # Only inject if thinking is not already set
        if "thinking" not in body:
            body["thinking"] = {"type": "enabled"}
            print(f"{YELLOW}[ZHIPU]{RESET} Injected thinking.type=enabled for {model}")
    
    return body


class StreamFilter:
    """
    A stateful stream filter that removes <think>...</think> blocks
    from SSE ream chunks while handling cross-chunk tag boundaries.
    """
    
    def __init__(self):
        self.buffer = ""
        self.inside_think = False
        self.potential_tag_start = ""
    
    def process_chunk(self, chunk):
        """
        Process a chunk of text, filtering out <think> blocks.
        Returns (text_to_forward, thinking_text).
        """
        text = self.buffer + chunk
        self.buffer = ""
        
        output = []
        thinking = []
        i = 0
        
        while i < len(text):
            if self.inside_think:
                # Look for </think>
                end_pos = text.find("</think>", i)
                if end_pos != -1:
                    # Found closing tag
                    thinking.append(text[i:end_pos])
                    self.inside_think = False
                    i = end_pos + len("</think>")
                else:
                    # Check if we might have a partial </think> at the end
                    partial_match = self._check_partial_end_tag(text, i)
                    if partial_match > 0:
                        thinking.append(text[i:len(text) - partial_match])
                        self.buffer = text[len(text) - partial_match:]
                        break
                    else:
                        thinking.append(text[i:])
                        break
            else:
                # Look for <think>
                start_pos = text.find("<think>", i)
                if start_pos != -1:
                    # Found opening tag
                    output.append(text[i:start_pos])
                    self.inside_think = True
                    i = start_pos + len("<think>")
                else:
                    # Check if we might have a partial <think> at the end
                    partial_match = self._check_partial_start_tag(text, i)
                    if partial_match > 0:
                        output.append(text[i:len(text) - partial_match])
                        self.buffer = text[len(text) - partial_match:]
                        break
                    else:
                        output.append(text[i:])
                        break
        
        return "".join(output), "".join(thinking)
    
    def _check_partial_start_tag(self, text, start_idx):
        """Check if text ends with a partial <think> tag."""
        tag = "<think>"
        remaining = text[start_idx:]
        for length in range(min(len(tag) - 1, len(remaining)), 0, -1):
            if remaining.endswith(tag[:length]):
                return length
        return 0
    
    def _check_partial_end_tag(self, text, start_idx):
        """Check if text ends with a partial </think> tag."""
        tag = "</think>"
        remaining = text[start_idx:]
        for length in range(min(len(tag) - 1, len(remaining)), 0, -1):
            if remaining.endswith(tag[:length]):
                return length
        return 0
    
    def flush(self):
        """Flush any remaining buffer content."""
        if self.buffer:
            if self.inside_think:
                result = ("", self.buffer)
            else:
                result = (self.buffer, "")
            self.buffer = ""
            return result
        return ("", "")


def process_sse_line(line, stream_filter):
    """
    Process a single SSE line, filtering <think> blocks from content.
    Returns (modified_line, thinking_content).
    """
    if not line.startswith("data: "):
        return line, ""
    
    data_str = line[6:]  # Remove "data: " prefix
    
    if data_str.strip() == "[DONE]":
        return line, ""
    
    try:
        data = json.loads(data_str)
    except json.JSONDecodeError:
        return line, ""
    
    # Extract content from the delta
    choices = data.get("choices", [])
    if not choices:
        # Pass through chunks without choices (e.g., prompt_filter_results from Azure/OpenAI)
        return f"data: {json.dumps(data)}", ""
    
    delta = choices[0].get("delta", {})
    
    # Handle reasoning_content field (Claude thinking models in streaming)
    reasoning_content = delta.pop("reasoning_content", None)
    if reasoning_content:
        # Print to console but don't forward (content only, no prefix)
        print_thinking(reasoning_content)
    
    # Handle reasoning field (some providers)
    reasoning = delta.pop("reasoning", None)
    if reasoning:
        print_thinking(reasoning)

    # Handle thinking field (e.g., some OpenAI-compatible providers / Zhipu)
    thinking_field = delta.pop("thinking", None)
    if thinking_field:
        if isinstance(thinking_field, str):
            print_thinking(thinking_field)
        elif isinstance(thinking_field, dict):
            text = thinking_field.get("content") or thinking_field.get("text")
            if isinstance(text, str) and text:
                print_thinking(text)
        else:
            # Best-effort: stringify non-empty values
            try:
                s = str(thinking_field)
            except Exception:
                s = ""
            if s:
                print_thinking(s)
    
    content = delta.get("content", "")
    
    if not content:
        # If we removed reasoning fields, still need to forward the modified chunk
        if reasoning_content or reasoning or thinking_field:
            return f"data: {json.dumps(data, ensure_ascii=False)}", ""
        return line, ""
    
    # Filter the content for <think> tags
    filtered_content, thinking_content = stream_filter.process_chunk(content)
    
    # Update the delta with filtered content
    if filtered_content:
        delta["content"] = filtered_content
        return f"data: {json.dumps(data, ensure_ascii=False)}", thinking_content
    elif thinking_content:
        # Only thinking content, don't forward this chunk
        return None, thinking_content
    else:
        return None, ""


def stream_response(upstream_response, api_format="openai", filter_thinking_tags=True, model=None):
    """Generator that streams filtered response."""
    # Only create filter if filtering is enabled
    stream_filter = StreamFilter() if filter_thinking_tags else None
    line_buffer = ""
    done_sent = False

    def _emit_final_flush():
        if stream_filter is None:
            return
        remaining, thinking = stream_filter.flush()
        if thinking:
            print_thinking(thinking)
        if remaining:
            final_chunk = {
                "choices": [{
                    "delta": {"content": remaining},
                    "index": 0,
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n"

    def _emit_done():
        yield "data: [DONE]\n"
    
    # Use iter_lines with proper UTF-8 decoding to avoid encoding issues
    # iter_content with decode_unicode=True can cause issues when charset is not properly set
    try:
        for chunk in upstream_response.iter_content(chunk_size=None):
            if not chunk:
                continue
            chunk = chunk.decode('utf-8', errors='replace')
            if not chunk:
                continue

            line_buffer += chunk

            while "\n" in line_buffer:
                line, line_buffer = line_buffer.split("\n", 1)
                line = line.strip()

                if not line:
                    yield "\n"
                    continue

                # OpenAI/Azure: upstream is already OpenAI-compatible SSE
                if api_format in ("openai", "azure-openai"):
                    if stream_filter is None:
                        yield line + "\n"
                        if line.startswith("data: ") and line[6:].strip() == "[DONE]":
                            done_sent = True
                            return
                        continue

                    if line.startswith("data: ") and line[6:].strip() == "[DONE]":
                        yield from _emit_final_flush()
                        yield from _emit_done()
                        done_sent = True
                        return

                    modified_line, thinking = process_sse_line(line, stream_filter)
                    if thinking:
                        print_thinking(thinking)
                    if modified_line:
                        yield modified_line + "\n"
                    continue

                # Other providers: transform upstream streaming chunks into OpenAI-compatible SSE
                if not line.startswith("data: "):
                    continue

                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    yield from _emit_final_flush()
                    yield from _emit_done()
                    done_sent = True
                    return

                try:
                    upstream_chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                openai_chunk = transform_stream_chunk(upstream_chunk, api_format)
                if openai_chunk is None:
                    continue

                openai_line = f"data: {json.dumps(openai_chunk, ensure_ascii=False)}"

                if stream_filter is None:
                    yield openai_line + "\n"
                    continue

                modified_line, thinking = process_sse_line(openai_line, stream_filter)
                if thinking:
                    print_thinking(thinking)
                if modified_line:
                    yield modified_line + "\n"

        # Process any remaining content in buffer
        if line_buffer.strip():
            line = line_buffer.strip()
            if api_format in ("openai", "azure-openai"):
                if stream_filter is None:
                    yield line + "\n"
                else:
                    if line.startswith("data: ") and line[6:].strip() == "[DONE]":
                        yield from _emit_final_flush()
                        yield from _emit_done()
                        done_sent = True
                    else:
                        modified_line, thinking = process_sse_line(line, stream_filter)
                        if thinking:
                            print_thinking(thinking)
                        if modified_line:
                            yield modified_line + "\n"
            else:
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        yield from _emit_final_flush()
                        yield from _emit_done()
                        done_sent = True
                    else:
                        try:
                            upstream_chunk = json.loads(data_str)
                            openai_chunk = transform_stream_chunk(upstream_chunk, api_format)
                        except json.JSONDecodeError:
                            openai_chunk = None
                        if openai_chunk is not None:
                            openai_line = f"data: {json.dumps(openai_chunk, ensure_ascii=False)}"
                            if stream_filter is None:
                                yield openai_line + "\n"
                            else:
                                modified_line, thinking = process_sse_line(openai_line, stream_filter)
                                if thinking:
                                    print_thinking(thinking)
                                if modified_line:
                                    yield modified_line + "\n"

        if not done_sent:
            yield from _emit_final_flush()
            yield from _emit_done()
    finally:
        try:
            upstream_response.close()
        except Exception:
            pass
        ThinkingPrinter.end()
        _broadcast_thinking({"type": "done", "model": model})


def filter_non_stream_response(response_data):
    """Filter thinking content from non-streaming response.
    
    Handles multiple formats:
    1. <think>...</think> tags in content (DeepSeek, Qwen)
    2. reasoning_content field (Claude/Anthropic via OpenAI-compatible API)
    3. reasoning field (some providers)
    """
    choices = response_data.get("choices", [])
    
    for choice in choices:
        message = choice.get("message", {})
        content = message.get("content", "")
        
        # Handle reasoning_content field (Claude thinking models)
        reasoning_content = message.pop("reasoning_content", None)
        if reasoning_content:
            print(f"\n{YELLOW}[THINKING]{RESET} (reasoning_content)")
            print(f"{DIM}{reasoning_content[:500]}{'...' if len(reasoning_content) > 500 else ''}{RESET}")
        
        # Handle reasoning field (some providers)
        reasoning = message.pop("reasoning", None)
        if reasoning:
            print(f"\n{YELLOW}[THINKING]{RESET} (reasoning)")
            print(f"{DIM}{reasoning[:500]}{'...' if len(reasoning) > 500 else ''}{RESET}")
        
        if content:
            # Extract and print thinking content from <think> tags
            think_pattern = re.compile(r"<think>(.*?)</think>", re.DOTALL)
            thinking_matches = think_pattern.findall(content)
            
            for thinking in thinking_matches:
                print(f"\n{YELLOW}[THINKING]{RESET} (<think> tag)")
                print(f"{DIM}{thinking[:500]}{'...' if len(thinking) > 500 else ''}{RESET}")
            
            # Remove thinking blocks from content
            filtered_content = think_pattern.sub("", content)
            message["content"] = filtered_content
    
    return response_data


@app.route("/v1/chat/completions", methods=["POST"])
@require_api_key
def chat_completions():
    """Handle chat completion requests."""
    try:
        # Get request body
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return {"error": "Invalid or missing JSON body"}, 400
        body = _prune_undefined(body)
        model = body.get("model", "") or ""

        messages = body.get("messages", [])
        if messages is None:
            messages = []
        if not isinstance(messages, list):
            return {"error": "messages must be a list"}, 400
        body["messages"] = messages

        original_keys = list(body.keys())
        original_thinking = body.get('thinking')
        original_reasoning_effort = body.get('reasoning_effort')
    
        # Log incoming request for debugging
        print(f"\n{CYAN}[REQUEST]{RESET} Model: {model}, Stream: {body.get('stream')}")
        print(f"{CYAN}[REQUEST]{RESET} Messages: {len(body.get('messages', []))} items")
    
        # Get effective config based on profile matching
        effective_config = CONFIG_MANAGER.get_effective_config(model)
        profile_name = effective_config.get("profile_name")
        if profile_name:
            print(f"{YELLOW}[PROFILE]{RESET} Matched profile: {profile_name}")
    
        # Debug: print original request params (before injection)
        print(f"{CYAN}[DEBUG ORIGINAL]{RESET} Keys: {original_keys}")
        print(f"{CYAN}[DEBUG ORIGINAL]{RESET} thinking: {original_thinking}, reasoning_effort: {original_reasoning_effort}")
    
        # Inject inference parameters with effective config
        body = inject_inference_params(body, effective_config)
        body = _prune_undefined(body)
    
        # Debug: print final request params (after injection)
        print(f"{CYAN}[DEBUG FINAL]{RESET} Keys: {list(body.keys())}")
        print(f"{CYAN}[DEBUG FINAL]{RESET} thinking: {body.get('thinking')}")
    
        # Get API key and base URL from effective config
        if CONFIG_MANAGER.proxy.api_key:
            api_key = effective_config.get("upstream_api_key") or UPSTREAM_API_KEY
        else:
            api_key = request.headers.get("Authorization", "").replace("Bearer ", "") or effective_config.get("upstream_api_key") or UPSTREAM_API_KEY
        base_url = request.headers.get("X-Upstream-Base-URL") or effective_config.get("upstream_base_url") or UPSTREAM_BASE_URL
    
        # Get API format from header or effective config
        api_format = request.headers.get("X-API-Format") or effective_config.get("upstream_api_format") or "openai"
    
        # Get the appropriate adapter for the API format
        adapter = get_adapter(api_format)
    
        # Transform request body for the target API format
        transformed_body = adapter.transform_request(body)
        transformed_body = _prune_undefined(transformed_body)
    
        # Get headers for the target API format
        headers = adapter.get_headers(api_key)
    
        # Get the endpoint for the target API format
        is_stream = body.get("stream", False)
        upstream_url = adapter.get_endpoint(base_url, model=model, stream=is_stream)
    
        print(f"\n{YELLOW}[PROXY]{RESET} Forwarding request to {upstream_url}")
        print(f"{YELLOW}[PROXY]{RESET} Stream mode: {is_stream}, API format: {api_format}")
    
        try:
            upstream_response = requests.post(
                upstream_url,
                headers=headers,
                json=transformed_body,
                stream=is_stream,
                timeout=300
            )
        except requests.RequestException as e:
            print(f"{RED}[ERROR]{RESET} Request failed: {e}")
            return {"error": str(e)}, 502

        # If upstream returns an error, pass through its status code (don't mask as 502)
        if upstream_response.status_code >= 400:
            try:
                err_json = upstream_response.json()
            except ValueError:
                err_json = {"error": upstream_response.text[:2000]}

            print(f"{RED}[UPSTREAM ERROR]{RESET} Status: {upstream_response.status_code}")
            print(f"{RED}[UPSTREAM ERROR]{RESET} Body: {str(err_json)[:500]}")

            # Ensure the client always gets JSON (not Werkzeug HTML)
            return {
                "error": err_json.get("error") if isinstance(err_json, dict) else err_json,
                "upstream_status": upstream_response.status_code,
                "upstream": err_json,
            }, upstream_response.status_code
    
        if is_stream:
            # Stream response with filtering
            filter_tags = effective_config.get("filter_thinking_tags", True)
            return Response(
                stream_with_context(stream_response(upstream_response, api_format, filter_tags, model=model)),
                content_type="text/event-stream; charset=utf-8",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            # Non-streaming response
            try:
                response_data = upstream_response.json()
            except ValueError:
                return {
                    "error": "Upstream returned non-JSON response",
                    "upstream_status": upstream_response.status_code,
                    "upstream_body": upstream_response.text[:500],
                }, 502
            # Transform response to OpenAI format if needed
            transformed_response = adapter.transform_response(response_data)
            filtered_data = filter_non_stream_response(transformed_response)
            return filtered_data

    except Exception as e:
        # Avoid returning Werkzeug HTML error pages to OpenAI-compatible clients.
        print(f"{RED}[FATAL]{RESET} Unhandled error in /v1/chat/completions: {e}")
        return {"error": "Internal proxy error", "detail": str(e)}, 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    profile = CONFIG_MANAGER.get_default_profile()
    upstream = profile.upstream.base_url if profile else UPSTREAM_BASE_URL
    return {"status": "healthy", "upstream": upstream}


@app.route("/v1/thinking/stream", methods=["GET"])
def thinking_stream():
    """SSE stream for captured thinking content (for frontend ThinkingViewer)."""

    def gen():
        q = queue.Queue()
        with _THINKING_LOCK:
            _THINKING_SUBSCRIBERS.append(q)

        try:
            while True:
                try:
                    data = q.get(timeout=15)
                    yield f"data: {data}\n\n"
                except queue.Empty:
                    # Keep-alive ping
                    yield ": ping\n\n"
        finally:
            with _THINKING_LOCK:
                try:
                    _THINKING_SUBSCRIBERS.remove(q)
                except ValueError:
                    pass

    return Response(
        stream_with_context(gen()),
        content_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/v1/config/reasoning/types", methods=["GET"])
def get_reasoning_types():
    """Get supported reasoning types and effort levels (for frontend dropdown)."""
    return get_reasoning_types_info()


@app.route("/v1/config/proxy", methods=["GET"])
def get_proxy_config():
    """Get current proxy configuration (for frontend)."""
    return CONFIG_MANAGER.proxy.to_dict(hide_secrets=True)


@app.route("/v1/config/proxy", methods=["PUT"])
def update_proxy_config():
    """Update proxy configuration."""
    data = request.get_json()
    if not data:
        return {"error": "No data provided"}, 400
    
    result = CONFIG_MANAGER.update_proxy_settings(data)
    
    if not result.get("success"):
        return {"error": result.get("error", "Unknown error")}, 400
    
    # Log the update
    if result.get("restart_required"):
        print(f"{YELLOW}[CONFIG]{RESET} Configuration updated. Restart required for port change.")
    else:
        print(f"{YELLOW}[CONFIG]{RESET} Configuration updated.")
    
    return result


# ============== Profile API ==============

@app.route("/v1/config/profiles", methods=["GET"])
def get_profiles():
    """Get all configuration profiles."""
    return {
        "profiles": CONFIG_MANAGER.get_all_profiles(),
        "default_profile": CONFIG_MANAGER.default_profile_id,
    }


@app.route("/v1/config/profiles", methods=["POST"])
def create_profile():
    """Create a new configuration profile."""
    data = request.get_json()
    if not data:
        return {"error": "No data provided"}, 400
    
    result = CONFIG_MANAGER.create_profile(data)
    if not result.get("success"):
        return {"error": result.get("error", "Unknown error")}, 400
    
    print(f"{YELLOW}[PROFILE]{RESET} Created profile: {data.get('name')}")
    return result


@app.route("/v1/config/profiles/<profile_id>", methods=["GET"])
def get_profile(profile_id):
    """Get a specific configuration profile."""
    profile = CONFIG_MANAGER.get_profile(profile_id)
    if not profile:
        return {"error": "Profile not found"}, 404
    return {"profile": profile.to_dict()}


@app.route("/v1/config/profiles/<profile_id>", methods=["PUT"])
def update_profile(profile_id):
    """Update a configuration profile."""
    data = request.get_json()
    if not data:
        return {"error": "No data provided"}, 400
    
    result = CONFIG_MANAGER.update_profile(profile_id, data)
    if not result.get("success"):
        return {"error": result.get("error", "Unknown error")}, 400
    
    print(f"{YELLOW}[PROFILE]{RESET} Updated profile: {profile_id}")
    return result


@app.route("/v1/config/profiles/<profile_id>", methods=["DELETE"])
def delete_profile(profile_id):
    """Delete a configuration profile."""
    result = CONFIG_MANAGER.delete_profile(profile_id)
    if not result.get("success"):
        return {"error": result.get("error", "Unknown error")}, 400
    
    print(f"{YELLOW}[PROFILE]{RESET} Deleted profile: {profile_id}")
    return result


@app.route("/v1/config/profiles/test", methods=["POST"])
def test_profile_match():
    """Test model name matching against profiles."""
    data = request.get_json()
    if not data or "model" not in data:
        return {"error": "Model name is required"}, 400
    
    result = CONFIG_MANAGER.test_match(data["model"])
    return result


@app.route("/v1/config/default-profile", methods=["PUT"])
def set_default_profile():
    """Set the default profile."""
    data = request.get_json()
    if not data or "profile_id" not in data:
        return {"error": "profile_id is required"}, 400
    
    result = CONFIG_MANAGER.set_default_profile(data["profile_id"])
    if not result.get("success"):
        return {"error": result.get("error", "Unknown error")}, 400
    
    print(f"{YELLOW}[PROFILE]{RESET} Default profile set to: {data['profile_id']}")
    return result


@app.route("/v1/config/export", methods=["GET"])
def export_config():
    """Export full configuration."""
    return CONFIG_MANAGER.export_config()


@app.route("/v1/config/import", methods=["POST"])
def import_config():
    """Import configuration."""
    data = request.get_json()
    if not data:
        return {"error": "No data provided"}, 400
    
    merge = request.args.get("merge", "true").lower() == "true"
    result = CONFIG_MANAGER.import_config(data, merge=merge)
    
    if not result.get("success"):
        return {"error": result.get("error", "Unknown error")}, 400
    
    print(f"{YELLOW}[CONFIG]{RESET} Imported {result.get('profiles_count', 0)} profiles")
    return result


@app.route("/v1/models", methods=["GET"])
@require_api_key
def list_models():
    """Proxy models endpoint."""
    # Get upstream api_key/base_url from headers or from default profile.
    # NOTE: When proxy api_key is enabled, request Authorization is used for proxy auth,
    # so upstream auth must come from config.
    default_profile = CONFIG_MANAGER.get_default_profile()
    profile_api_key = default_profile.upstream.api_key if default_profile else UPSTREAM_API_KEY
    profile_base_url = default_profile.upstream.base_url if default_profile else UPSTREAM_BASE_URL

    base_url = request.headers.get("X-Upstream-Base-URL") or profile_base_url

    if CONFIG_MANAGER.proxy.api_key:
        api_key = profile_api_key
    else:
        api_key = request.headers.get("Authorization", "").replace("Bearer ", "") or profile_api_key
    
    headers = {"Authorization": f"Bearer {api_key}"}
    upstream_url = f"{base_url.rstrip('/')}/v1/models"
    
    try:
        response = requests.get(upstream_url, headers=headers, timeout=30)
        try:
            return response.json(), response.status_code
        except ValueError:
            return {"error": "Upstream returned non-JSON response", "upstream_body": response.text[:500]}, 502
    except requests.RequestException as e:
        return {"error": str(e)}, 502


if __name__ == "__main__":
    print(f"{YELLOW}=" * 60 + RESET)
    print(f"{YELLOW}Droid BYOK Proxy Server{RESET}")
    print(f"{YELLOW}=" * 60 + RESET)
    print(f"Default Upstream: {UPSTREAM_BASE_URL}")
    print(f"Listening on: http://localhost:{PROXY_PORT}")
    print(f"{YELLOW}=" * 60 + RESET)
    
    if not UPSTREAM_API_KEY:
        print(f"\n{YELLOW}[WARNING]{RESET} No API key configured in default profile!")
    
    # Print profiles summary
    profiles = CONFIG_MANAGER.profiles
    print(f"\n{CYAN}[PROFILES]{RESET} {len(profiles)} profile(s) loaded:")
    for p in profiles:
        status = "enabled" if p.enabled else "disabled"
        reasoning_status = f"reasoning={p.reasoning.type}" if p.reasoning.enabled else "no reasoning"
        print(f"  - {p.name} ({status}, {reasoning_status})")
        if p.model_patterns:
            print(f"    Patterns: {', '.join(p.model_patterns)}")
    
    print(f"\n{CYAN}[DEFAULT]{RESET} {CONFIG_MANAGER.default_profile_id}")
    print(f"{YELLOW}=" * 60 + RESET)
    
    app.run(host="0.0.0.0", port=PROXY_PORT, debug=False, threaded=True)
