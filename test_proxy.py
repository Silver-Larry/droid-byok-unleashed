"""
Droid BYOK Proxy 端到端测试脚本
测试代理服务的连通性和功能
"""

import requests
import json
import sys

PROXY_URL = "http://localhost:5000"
PROXY_API_KEY = "123456"  # proxy_config.json 中配置的 proxy_api_key

def print_result(name, success, detail=""):
    status = "✓ PASS" if success else "✗ FAIL"
    print(f"[{status}] {name}")
    if detail:
        print(f"        {detail}")

def test_health():
    """测试健康检查端点"""
    try:
        r = requests.get(f"{PROXY_URL}/health", timeout=5)
        data = r.json()
        success = r.status_code == 200 and data.get("status") == "healthy"
        print_result("Health Check", success, f"upstream: {data.get('upstream')}")
        return success
    except Exception as e:
        print_result("Health Check", False, str(e))
        return False

def test_config():
    """测试配置端点"""
    try:
        r = requests.get(f"{PROXY_URL}/v1/config/proxy", timeout=5)
        data = r.json()
        success = r.status_code == 200
        print_result("Get Proxy Config", success, 
                    f"port={data.get('proxy_port')}, url={data.get('upstream_base_url')}, format={data.get('upstream_api_format')}")
        return success
    except Exception as e:
        print_result("Get Proxy Config", False, str(e))
        return False

def test_auth_required():
    """测试无认证时应该返回 401"""
    try:
        r = requests.post(
            f"{PROXY_URL}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}]},
            timeout=5
        )
        success = r.status_code == 401
        print_result("Auth Required (no key)", success, f"status={r.status_code}")
        return success
    except Exception as e:
        print_result("Auth Required (no key)", False, str(e))
        return False

def test_auth_invalid():
    """测试错误的 API Key"""
    try:
        r = requests.post(
            f"{PROXY_URL}/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer wrong-key"
            },
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}]},
            timeout=5
        )
        success = r.status_code == 401
        print_result("Auth Invalid Key", success, f"status={r.status_code}")
        return success
    except Exception as e:
        print_result("Auth Invalid Key", False, str(e))
        return False

def test_models():
    """测试模型列表端点"""
    try:
        r = requests.get(
            f"{PROXY_URL}/v1/models",
            headers={"Authorization": f"Bearer {PROXY_API_KEY}"},
            timeout=30
        )
        success = r.status_code == 200
        data = r.json() if success else {}
        model_count = len(data.get("data", []))
        print_result("List Models", success, f"status={r.status_code}, models={model_count}")
        if not success:
            print(f"        Response: {r.text[:200]}")
        return success
    except Exception as e:
        print_result("List Models", False, str(e))
        return False

def test_chat_non_stream():
    """测试非流式聊天"""
    try:
        r = requests.post(
            f"{PROXY_URL}/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {PROXY_API_KEY}"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Say 'test ok' in 2 words"}],
                "max_tokens": 10,
                "stream": False
            },
            timeout=30
        )
        success = r.status_code == 200
        data = r.json() if success else {}
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        print_result("Chat (non-stream)", success, f"status={r.status_code}, response='{content[:50]}'")
        if not success:
            print(f"        Response: {r.text[:300]}")
        return success
    except Exception as e:
        print_result("Chat (non-stream)", False, str(e))
        return False

def test_chat_stream():
    """测试流式聊天"""
    try:
        r = requests.post(
            f"{PROXY_URL}/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {PROXY_API_KEY}"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Say 'stream ok'"}],
                "max_tokens": 10,
                "stream": True
            },
            timeout=30,
            stream=True
        )
        
        if r.status_code != 200:
            print_result("Chat (stream)", False, f"status={r.status_code}, response={r.text[:200]}")
            return False
        
        chunks = []
        for line in r.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content:
                        chunks.append(content)
                except json.JSONDecodeError:
                    pass
        
        full_response = "".join(chunks)
        success = len(chunks) > 0
        print_result("Chat (stream)", success, f"chunks={len(chunks)}, response='{full_response[:50]}'")
        return success
    except Exception as e:
        print_result("Chat (stream)", False, str(e))
        return False

def test_droid_simulation():
    """模拟 Droid CLI 的调用方式"""
    print("\n--- Droid CLI 模拟测试 ---")
    try:
        # Droid CLI 通常使用流式请求
        r = requests.post(
            f"{PROXY_URL}/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {PROXY_API_KEY}",
                "User-Agent": "Droid-CLI-Test"
            },
            json={
                "model": "gpt-4o-mini",  # 或者你在 Droid 中配置的模型名
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "What is 2+2? Answer with just the number."}
                ],
                "stream": True,
                "temperature": 0.7
            },
            timeout=60,
            stream=True
        )
        
        print(f"Status Code: {r.status_code}")
        print(f"Headers: {dict(r.headers)}")
        
        if r.status_code != 200:
            print(f"Error Response: {r.text[:500]}")
            print_result("Droid Simulation", False, f"status={r.status_code}")
            return False
        
        print("Streaming response:")
        chunks = []
        for line in r.iter_lines(decode_unicode=True):
            if line:
                print(f"  RAW: {line[:100]}")
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        print("  [DONE received]")
                        break
                    try:
                        data = json.loads(data_str)
                        content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            chunks.append(content)
                            print(f"  CONTENT: '{content}'")
                    except json.JSONDecodeError as e:
                        print(f"  JSON ERROR: {e}")
        
        full_response = "".join(chunks)
        success = len(full_response) > 0
        print_result("Droid Simulation", success, f"Full response: '{full_response}'")
        return success
    except Exception as e:
        print_result("Droid Simulation", False, str(e))
        return False

def main():
    print("=" * 60)
    print("Droid BYOK Proxy 端到端测试")
    print("=" * 60)
    print(f"Proxy URL: {PROXY_URL}")
    print(f"Proxy API Key: {PROXY_API_KEY}")
    print("=" * 60)
    print()
    
    results = []
    
    # 基础连通性测试
    print("--- 基础连通性测试 ---")
    results.append(("Health Check", test_health()))
    results.append(("Config", test_config()))
    print()
    
    # 认证测试
    print("--- 认证测试 ---")
    results.append(("Auth Required", test_auth_required()))
    results.append(("Auth Invalid", test_auth_invalid()))
    print()
    
    # API 功能测试
    print("--- API 功能测试 ---")
    results.append(("Models", test_models()))
    results.append(("Chat Non-Stream", test_chat_non_stream()))
    results.append(("Chat Stream", test_chat_stream()))
    
    # Droid 模拟测试
    results.append(("Droid Simulation", test_droid_simulation()))
    
    # 汇总
    print()
    print("=" * 60)
    print("测试汇总")
    print("=" * 60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {name}")
    print()
    print(f"通过: {passed}/{total}")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
