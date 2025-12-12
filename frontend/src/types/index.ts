export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  thinking?: string;
  timestamp: Date;
}

export interface LLMParams {
  temperature?: number | null;
  top_p?: number | null;
  top_k?: number | null;
  max_tokens?: number | null;
  presence_penalty?: number | null;
  frequency_penalty?: number | null;
  seed?: number | null;
  stop?: string[];
}

export interface ChatCompletionRequest {
  model: string;
  messages: { role: string; content: string }[];
  stream?: boolean;
  temperature?: number;
  top_p?: number;
  top_k?: number;
  max_tokens?: number;
  presence_penalty?: number;
  frequency_penalty?: number;
  seed?: number;
  stop?: string[];
}

export interface Model {
  id: string;
  object: string;
  created?: number;
  owned_by?: string;
}

export interface ModelsResponse {
  data: Model[];
  object: string;
}

export interface HealthResponse {
  status: string;
  upstream: string;
}

// Reasoning Model Configuration Types
export type ReasoningType =
  | 'deepseek'
  | 'openai'
  | 'anthropic'
  | 'gemini'
  | 'qwen'
  | 'openrouter'
  | 'custom';

export type ReasoningEffort =
  | 'none'
  | 'minimal'
  | 'low'
  | 'medium'
  | 'high'
  | 'auto';

export interface ReasoningConfig {
  enabled: boolean;
  reasoning_type: ReasoningType;
  effort: ReasoningEffort;
  budget_tokens: number | null;
  custom_params: Record<string, unknown>;
  filter_thinking_tags: boolean;
}

export interface ReasoningTypeInfo {
  value: ReasoningType;
  label: string;
  description: string;
  supported_efforts: ReasoningEffort[];
}

export interface ReasoningTypesResponse {
  types: ReasoningTypeInfo[];
  efforts: { value: ReasoningEffort; label: string }[];
}

// Proxy Configuration Types
export interface ProxyConfig {
  proxy_port: number;
  proxy_api_key: string;
  upstream_api_key: string;
  upstream_base_url: string;
}

export interface ProxyConfigUpdateResponse {
  success: boolean;
  restart_required: boolean;
  config: ProxyConfig;
}

// API Format Types (inspired by cherry-studio)
export type ApiFormatType =
  | 'openai'
  | 'openai-response'
  | 'anthropic'
  | 'gemini'
  | 'azure-openai';

export interface ApiFormatOption {
  value: ApiFormatType;
  label: string;
  description: string;
}

export const API_FORMAT_OPTIONS: ApiFormatOption[] = [
  { value: 'openai', label: 'OpenAI', description: 'OpenAI compatible API (default)' },
  { value: 'openai-response', label: 'OpenAI Response API', description: 'OpenAI Response API format' },
  { value: 'anthropic', label: 'Anthropic', description: 'Anthropic Claude API format' },
  { value: 'gemini', label: 'Google (Gemini)', description: 'Google Gemini API format' },
  { value: 'azure-openai', label: 'Azure OpenAI', description: 'Azure OpenAI Service format' },
];

// Thinking content for display
export interface ThinkingContent {
  id: string;
  content: string;
  timestamp: Date;
  model?: string;
}

// Match types for model patterns
export type MatchType = 'exact' | 'wildcard' | 'regex';

// Upstream configuration
export interface UpstreamConfig {
  base_url: string;
  api_key: string;
  api_format: ApiFormatType;
}

// LLM parameters for Profile (reuses LLMParams defined above)

// Reasoning parameters
export interface ReasoningParams {
  enabled: boolean;
  type: ReasoningType;
  effort: ReasoningEffort;
  budget_tokens?: number | null;
  custom_params?: Record<string, unknown>;
  filter_thinking_tags: boolean;
}

// Unified Profile Configuration
export interface Profile {
  id: string;
  name: string;
  model_patterns: string[];
  match_type: MatchType;
  priority: number;
  enabled: boolean;
  upstream: UpstreamConfig;
  llm_params: LLMParams;
  reasoning: ReasoningParams;
  created_at: string;
  updated_at: string;
}

// API Response types
export interface ProfilesResponse {
  profiles: Profile[];
  default_profile: string;
}

export interface ProfileTestResult {
  model: string;
  matched: Profile | null;
  all_matches: {
    id: string;
    name: string;
    patterns: string[];
    match_type: MatchType;
    priority: number;
    enabled: boolean;
  }[];
}

// Proxy settings
export interface ProxySettings {
  port: number;
  api_key: string;
}

// Export/Import config
export interface ExportedConfig {
  proxy: ProxySettings;
  profiles: Profile[];
  default_profile: string;
}
