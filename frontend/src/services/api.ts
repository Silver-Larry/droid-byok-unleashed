import type { ModelsResponse, HealthResponse, LLMParams, ReasoningConfig, ReasoningTypesResponse, ProxyConfig, ProxyConfigUpdateResponse } from '../types';
import type { Config } from '../hooks/useConfig';

const API_BASE = '';

function getHeaders(config: Config): HeadersInit {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (config.apiKey) {
    headers['Authorization'] = `Bearer ${config.apiKey}`;
  }
  if (config.baseUrl) {
    headers['X-Upstream-Base-URL'] = config.baseUrl;
  }
  return headers;
}

export async function fetchModels(config: Config): Promise<ModelsResponse> {
  const response = await fetch(`${API_BASE}/v1/models`, {
    headers: getHeaders(config),
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch models: ${response.statusText}`);
  }
  return response.json();
}

export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchReasoningConfig(): Promise<ReasoningConfig> {
  const response = await fetch(`${API_BASE}/v1/config/reasoning`);
  if (!response.ok) {
    throw new Error(`Failed to fetch reasoning config: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchReasoningTypes(): Promise<ReasoningTypesResponse> {
  const response = await fetch(`${API_BASE}/v1/config/reasoning/types`);
  if (!response.ok) {
    throw new Error(`Failed to fetch reasoning types: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchProxyConfig(): Promise<ProxyConfig> {
  const response = await fetch(`${API_BASE}/v1/config/proxy`);
  if (!response.ok) {
    throw new Error(`Failed to fetch proxy config: ${response.statusText}`);
  }
  return response.json();
}

export async function updateProxyConfig(config: Partial<ProxyConfig>): Promise<ProxyConfigUpdateResponse> {
  const response = await fetch(`${API_BASE}/v1/config/proxy`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!response.ok) {
    throw new Error(`Failed to update proxy config: ${response.statusText}`);
  }
  return response.json();
}

export async function* streamChat(
  model: string,
  messages: { role: string; content: string }[],
  params: LLMParams,
  config: Config
): AsyncGenerator<string, void, unknown> {
  const body: Record<string, unknown> = {
    model,
    messages,
    stream: true,
  };

  // Only add non-null/undefined parameters
  if (params.temperature !== undefined) body.temperature = params.temperature;
  if (params.top_p !== undefined) body.top_p = params.top_p;
  if (params.top_k !== undefined) body.top_k = params.top_k;
  if (params.max_tokens !== undefined) body.max_tokens = params.max_tokens;
  if (params.presence_penalty !== undefined) body.presence_penalty = params.presence_penalty;
  if (params.frequency_penalty !== undefined) body.frequency_penalty = params.frequency_penalty;
  if (params.seed !== undefined) body.seed = params.seed;
  if (params.stop?.length) body.stop = params.stop;

  const response = await fetch(`${API_BASE}/v1/chat/completions`, {
    method: 'POST',
    headers: getHeaders(config),
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || !trimmed.startsWith('data: ')) continue;

      const data = trimmed.slice(6);
      if (data === '[DONE]') return;

      try {
        const parsed = JSON.parse(data);
        const content = parsed.choices?.[0]?.delta?.content;
        if (content) {
          yield content;
        }
      } catch {
        // Skip invalid JSON
      }
    }
  }
}
