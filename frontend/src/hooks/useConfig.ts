import { useState, useEffect } from 'react';
import type { ReasoningType, ReasoningEffort, ApiFormatType } from '../types';

export interface Config {
  apiKey: string;
  baseUrl: string;
  apiFormat: ApiFormatType;
  // LLM Parameters
  temperature: number;
  topP: number;
  topK: number | null;
  maxTokens: number | null;
  presencePenalty: number;
  frequencyPenalty: number;
  seed: number | null;
  // Reasoning Model Configuration
  reasoningEnabled: boolean;
  reasoningType: ReasoningType;
  reasoningEffort: ReasoningEffort;
  reasoningBudgetTokens: number | null;
  reasoningCustomParams: string;
  filterThinkingTags: boolean;
}

const STORAGE_KEY = 'droid-proxy-config';

const defaultConfig: Config = {
  apiKey: '',
  baseUrl: '',
  apiFormat: 'openai',
  temperature: 0.7,
  topP: 1,
  topK: null,
  maxTokens: null,
  presencePenalty: 0,
  frequencyPenalty: 0,
  seed: null,
  // Reasoning defaults
  reasoningEnabled: false,
  reasoningType: 'deepseek',
  reasoningEffort: 'auto',
  reasoningBudgetTokens: null,
  reasoningCustomParams: '{}',
  filterThinkingTags: true,
};

export function useConfig() {
  const [config, setConfig] = useState<Config>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        return { ...defaultConfig, ...JSON.parse(saved) };
      } catch {
        return defaultConfig;
      }
    }
    return defaultConfig;
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
  }, [config]);

  const updateConfig = (updates: Partial<Config>) => {
    setConfig(prev => ({ ...prev, ...updates }));
  };

  return { config, updateConfig };
}
