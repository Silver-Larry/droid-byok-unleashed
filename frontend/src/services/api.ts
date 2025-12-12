import type { 
  ModelsResponse, 
  HealthResponse, 
  LLMParams, 
  ReasoningTypesResponse, 
  Profile, 
  ProfilesResponse, 
  ProfileTestResult,
  ProxySettings,
  ExportedConfig,
} from '../types';
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

export async function fetchReasoningTypes(): Promise<ReasoningTypesResponse> {
  const response = await fetch(`${API_BASE}/v1/config/reasoning/types`);
  if (!response.ok) {
    throw new Error(`Failed to fetch reasoning types: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchProxyConfig(): Promise<ProxySettings> {
  const response = await fetch(`${API_BASE}/v1/config/proxy`);
  if (!response.ok) {
    throw new Error(`Failed to fetch proxy config: ${response.statusText}`);
  }
  return response.json();
}

export async function updateProxyConfig(config: Partial<ProxySettings>): Promise<{ success: boolean; restart_required: boolean; proxy: ProxySettings }> {
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

// ============== Profile API ==============

export async function fetchProfiles(): Promise<ProfilesResponse> {
  const response = await fetch(`${API_BASE}/v1/config/profiles`);
  if (!response.ok) {
    throw new Error(`Failed to fetch profiles: ${response.statusText}`);
  }
  return response.json();
}

export async function createProfile(profile: Partial<Profile>): Promise<{ success: boolean; profile?: Profile; error?: string }> {
  const response = await fetch(`${API_BASE}/v1/config/profiles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profile),
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.error || `Failed to create profile: ${response.statusText}`);
  }
  return response.json();
}

export async function updateProfile(profileId: string, updates: Partial<Profile>): Promise<{ success: boolean; profile?: Profile; error?: string }> {
  const response = await fetch(`${API_BASE}/v1/config/profiles/${profileId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.error || `Failed to update profile: ${response.statusText}`);
  }
  return response.json();
}

export async function deleteProfile(profileId: string): Promise<{ success: boolean; error?: string }> {
  const response = await fetch(`${API_BASE}/v1/config/profiles/${profileId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.error || `Failed to delete profile: ${response.statusText}`);
  }
  return response.json();
}

export async function testProfileMatch(model: string): Promise<ProfileTestResult> {
  const response = await fetch(`${API_BASE}/v1/config/profiles/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model }),
  });
  if (!response.ok) {
    throw new Error(`Failed to test profile match: ${response.statusText}`);
  }
  return response.json();
}

export async function setDefaultProfile(profileId: string): Promise<{ success: boolean; error?: string }> {
  const response = await fetch(`${API_BASE}/v1/config/default-profile`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile_id: profileId }),
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.error || `Failed to set default profile: ${response.statusText}`);
  }
  return response.json();
}

export async function exportConfig(): Promise<ExportedConfig> {
  const response = await fetch(`${API_BASE}/v1/config/export`);
  if (!response.ok) {
    throw new Error(`Failed to export config: ${response.statusText}`);
  }
  return response.json();
}

export async function importConfig(config: ExportedConfig, merge = true): Promise<{ success: boolean; profiles_count?: number; error?: string }> {
  const response = await fetch(`${API_BASE}/v1/config/import?merge=${merge}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.error || `Failed to import config: ${response.statusText}`);
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
