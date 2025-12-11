export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  thinking?: string;
  timestamp: Date;
}

export interface LLMParams {
  temperature?: number;
  top_p?: number;
  top_k?: number;
  max_tokens?: number;
  presence_penalty?: number;
  frequency_penalty?: number;
  seed?: number;
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
