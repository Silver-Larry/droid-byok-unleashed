import { useState, useCallback, useMemo } from 'react';
import type { Message, LLMParams } from '../types';
import type { Config } from './useConfig';
import { streamChat } from '../services/api';

export function useChat(model: string, config: Config) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const llmParams = useMemo<LLMParams>(() => {
    const params: LLMParams = {};
    if (config.temperature !== undefined) params.temperature = config.temperature;
    if (config.topP !== undefined) params.top_p = config.topP;
    if (config.topK !== null) params.top_k = config.topK;
    if (config.maxTokens !== null) params.max_tokens = config.maxTokens;
    if (config.presencePenalty !== undefined) params.presence_penalty = config.presencePenalty;
    if (config.frequencyPenalty !== undefined) params.frequency_penalty = config.frequencyPenalty;
    if (config.seed !== null) params.seed = config.seed;
    return params;
  }, [config]);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    const assistantMessage: Message = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, assistantMessage]);

    try {
      const chatMessages = [...messages, userMessage].map(m => ({
        role: m.role,
        content: m.content,
      }));

      for await (const chunk of streamChat(model, chatMessages, llmParams, config)) {
        setMessages(prev => {
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          updated[lastIdx] = {
            ...updated[lastIdx],
            content: updated[lastIdx].content + chunk,
          };
          return updated;
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  }, [messages, model, llmParams, config, isLoading]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, isLoading, error, sendMessage, clearMessages };
}
