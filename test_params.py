"""Unit tests for LLM parameter handling functions."""

import os
import sys
sys.path.insert(0, "D:\\demo\\droid-byok-unleashed")

from proxy import (
    get_default_params,
    validate_param,
    merge_params,
    sanitize_params,
    inject_inference_params,
    LLM_PARAMS_CONFIG
)


def test_get_default_params_empty():
    """Test get_default_params with no env vars set."""
    # Clear any existing env vars
    for param in LLM_PARAMS_CONFIG.keys():
        env_key = f"DEFAULT_{param.upper()}"
        if env_key in os.environ:
            del os.environ[env_key]
    
    defaults = get_default_params()
    assert defaults == {}, f"Expected empty dict, got {defaults}"
    print("[PASS] get_default_params with no env vars")


def test_get_default_params_with_env():
    """Test get_default_params with env vars set."""
    os.environ["DEFAULT_TEMPERATURE"] = "0.8"
    os.environ["DEFAULT_TOP_P"] = "0.95"
    os.environ["DEFAULT_MAX_TOKENS"] = "2048"
    
    defaults = get_default_params()
    
    assert defaults["temperature"] == 0.8, f"Expected 0.8, got {defaults.get('temperature')}"
    assert defaults["top_p"] == 0.95, f"Expected 0.95, got {defaults.get('top_p')}"
    assert defaults["max_tokens"] == 2048, f"Expected 2048, got {defaults.get('max_tokens')}"
    
    # Cleanup
    del os.environ["DEFAULT_TEMPERATURE"]
    del os.environ["DEFAULT_TOP_P"]
    del os.environ["DEFAULT_MAX_TOKENS"]
    
    print("[PASS] get_default_params with env vars")


def test_validate_param_valid():
    """Test validate_param with valid values."""
    config = {"type": float, "range": (0, 2)}
    
    is_valid, warning = validate_param("temperature", 0.7, config)
    assert is_valid is True
    assert warning is None
    
    is_valid, warning = validate_param("temperature", 0, config)
    assert is_valid is True
    
    is_valid, warning = validate_param("temperature", 2, config)
    assert is_valid is True
    
    print("[PASS] validate_param with valid values")


def test_validate_param_invalid_range():
    """Test validate_param with out-of-range values."""
    config = {"type": float, "range": (0, 2)}
    
    is_valid, warning = validate_param("temperature", 2.5, config)
    assert is_valid is False
    assert "out of range" in warning
    
    is_valid, warning = validate_param("temperature", -0.5, config)
    assert is_valid is False
    
    print("[PASS] validate_param with invalid range")


def test_validate_param_none():
    """Test validate_param with None value."""
    config = {"type": float, "range": (0, 2)}
    
    is_valid, warning = validate_param("temperature", None, config)
    assert is_valid is True
    assert warning is None
    
    print("[PASS] validate_param with None")


def test_merge_params():
    """Test merge_params function."""
    body = {"temperature": 0.5, "model": "test-model"}
    defaults = {"temperature": 0.7, "top_p": 0.9, "max_tokens": 4096}
    
    result = merge_params(body, defaults)
    
    # Request params should take precedence
    assert result["temperature"] == 0.5, "Request param should override default"
    # Defaults should be added
    assert result["top_p"] == 0.9, "Default should be added"
    assert result["max_tokens"] == 4096, "Default should be added"
    # Original params should be preserved
    assert result["model"] == "test-model", "Original param should be preserved"
    
    print("[PASS] merge_params")


def test_sanitize_params_removes_none():
    """Test sanitize_params removes None values."""
    body = {"temperature": 0.7, "top_p": None, "max_tokens": 1000}
    
    result = sanitize_params(body)
    
    assert "temperature" in result
    assert "top_p" not in result, "None value should be removed"
    assert "max_tokens" in result
    
    print("[PASS] sanitize_params removes None")


def test_inject_inference_params_full():
    """Test inject_inference_params with defaults and request params."""
    # Set some defaults
    os.environ["DEFAULT_TEMPERATURE"] = "0.7"
    os.environ["DEFAULT_TOP_P"] = "0.9"
    
    body = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "Hello"}],
        "temperature": 0.5,  # Override default
        "max_tokens": 2000
    }
    
    result = inject_inference_params(body)
    
    # Request param should override default
    assert result["temperature"] == 0.5
    # Default should be added
    assert result["top_p"] == 0.9
    # Request param should be preserved
    assert result["max_tokens"] == 2000
    assert result["model"] == "deepseek-chat"
    
    # Cleanup
    del os.environ["DEFAULT_TEMPERATURE"]
    del os.environ["DEFAULT_TOP_P"]
    
    print("[PASS] inject_inference_params full test")


def test_passthrough_params():
    """Test that unknown params are passed through."""
    body = {
        "model": "test",
        "messages": [],
        "custom_param": "value",
        "stop": ["END"],
        "temperature": 0.7
    }
    
    result = inject_inference_params(body)
    
    assert result["custom_param"] == "value", "Custom param should be preserved"
    assert result["stop"] == ["END"], "Stop sequences should be preserved"
    
    print("[PASS] passthrough params")


if __name__ == "__main__":
    print("Running LLM parameter handling tests...\n")
    
    test_get_default_params_empty()
    test_get_default_params_with_env()
    test_validate_param_valid()
    test_validate_param_invalid_range()
    test_validate_param_none()
    test_merge_params()
    test_sanitize_params_removes_none()
    test_inject_inference_params_full()
    test_passthrough_params()
    
    print("\n[ALL TESTS PASSED]")
